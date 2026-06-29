#!/usr/bin/env python3
"""Check auditable cinematic hero rubric — technical gates only (no human vision scoring)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "cinematic_hero_rubric_check_v1_latest.json"
RUBRIC_SSOT = ART / "cinematic_identity_drift_rubric_v1.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def probe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "exists": False}
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    if p.returncode != 0:
        return {"ok": False, "exists": True, "error": (p.stderr or "")[-300:]}
    data = json.loads(p.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    return {
        "ok": True,
        "exists": True,
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration_sec": float(fmt.get("duration") or 0.0),
        "bytes": int(float(fmt.get("size") or 0)),
    }


def evaluate_report(report: dict[str, Any], *, variant: str, rubric: dict[str, Any]) -> dict[str, Any]:
    min_bytes = int(rubric.get("min_clip_bytes") or 50_000)
    min_dur = float(rubric.get("min_duration_sec") or 4.0)
    aligned = bool(report.get("scenario_aligned"))
    shots_out: list[dict[str, Any]] = []
    failures: list[str] = []

    master = (report.get("outputs") or {}).get("master_mp4")
    master_p = probe(Path(master)) if master else {"ok": False}
    if not master_p.get("ok"):
        failures.append(f"{variant}_master_missing_or_bad")

    for item in (report.get("hero_shots") or []) + (report.get("animatic_tail") or []):
        shot = int(item.get("shot") or 0)
        clip = Path(str(item.get("clip") or ""))
        mode = str(item.get("mode") or "")
        info = probe(clip)
        row: dict[str, Any] = {
            "variant": variant,
            "shot": shot,
            "mode": mode,
            "clip": str(clip),
            "probe": info,
        }
        if not info.get("ok"):
            failures.append(f"{variant}_shot_{shot:02d}_clip_bad")
            row["pass"] = False
        elif info.get("bytes", 0) < min_bytes and mode == "reuse_donor_pack":
            failures.append(f"{variant}_shot_{shot:02d}_bytes_low")
            row["pass"] = False
        elif info.get("duration_sec", 0) < min_dur:
            failures.append(f"{variant}_shot_{shot:02d}_duration_low")
            row["pass"] = False
        else:
            row["pass"] = True

        if shot <= int(report.get("veo_shots") or 3):
            row["identity_drift_expected"] = mode == "reuse_donor_pack"
            row["human_identity_drift_yn"] = "Y" if mode == "reuse_donor_pack" else "N"
        else:
            row["identity_drift_expected"] = False
            row["human_identity_drift_yn"] = "N"

        row["scenario_aligned"] = aligned and not row["identity_drift_expected"]
        shots_out.append(row)

    veo = report.get("veo") or {}
    if veo.get("api_called"):
        failures.append(f"{variant}_unexpected_veo_api")

    return {
        "variant": variant,
        "ok": not failures,
        "scenario_aligned": aligned,
        "failures": failures,
        "master_probe": master_p,
        "shots": shots_out,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--economy-report", type=Path, default=ART / "auditable_cinematic_poc_economy_latest.json")
    ap.add_argument("--hybrid-report", type=Path, default=ART / "auditable_cinematic_poc_hybrid_latest.json")
    ap.add_argument("--rubric-json", type=Path, default=RUBRIC_SSOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rubric = load(args.rubric_json if args.rubric_json.is_absolute() else ROOT / args.rubric_json)
    economy = load(args.economy_report if args.economy_report.is_absolute() else ROOT / args.economy_report)
    hybrid = load(args.hybrid_report if args.hybrid_report.is_absolute() else ROOT / args.hybrid_report)

    economy_eval = evaluate_report(economy, variant="economy", rubric=rubric)
    hybrid_eval = evaluate_report(hybrid, variant="hybrid", rubric=rubric) if hybrid else {"ok": False, "skipped": True}

    ok = economy_eval.get("ok") and (hybrid_eval.get("ok") or hybrid_eval.get("skipped"))
    doc = {
        "schema": "cinematic_hero_rubric_check_v1",
        "generated_at_utc": now_utc(),
        "ok": ok,
        "rubric_ssot": str(args.rubric_json),
        "send_gate": "HOLD",
        "promotion": "infra_only",
        "economy": economy_eval,
        "hybrid": hybrid_eval,
        "reproduce_cmd": "py scripts/cinematic/check_cinematic_hero_rubric_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out_json": str(args.out_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
