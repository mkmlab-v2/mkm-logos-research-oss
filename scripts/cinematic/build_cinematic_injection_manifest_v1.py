#!/usr/bin/env python3
"""Build injection manifest for economy vs hybrid auditable cinematic PoC (disk only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "cinematic_injection_manifest_v1_latest.json"
CLIP_DONOR = ART / "cinematic_consistency_pack_v1"
DONOR_SCENARIO = ART / "cinematic_scenario_sample_v1.txt"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def shot_rows(report: dict[str, Any], *, aligned: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in report.get("hero_shots") or []:
        shot = int(item.get("shot") or 0)
        mode = str(item.get("mode") or "")
        rows.append(
            {
                "shot": shot,
                "mode": mode,
                "clip": item.get("clip"),
                "donor": item.get("donor"),
                "scenario_aligned": aligned and mode.startswith("animatic_hero_economy"),
                "identity_drift_expected": (not aligned) and mode == "reuse_donor_pack",
                "note": item.get("note"),
            }
        )
    for item in report.get("animatic_tail") or []:
        shot = int(item.get("shot") or 0)
        rows.append(
            {
                "shot": shot,
                "mode": item.get("mode") or "animatic_local_ffmpeg",
                "clip": item.get("clip"),
                "donor": None,
                "scenario_aligned": True,
                "identity_drift_expected": False,
                "note": "meta_bridge_tail",
            }
        )
    rows.sort(key=lambda r: r["shot"])
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--economy-report", type=Path, default=ART / "auditable_cinematic_poc_economy_latest.json")
    ap.add_argument("--hybrid-report", type=Path, default=ART / "auditable_cinematic_poc_hybrid_latest.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    economy = load(args.economy_report if args.economy_report.is_absolute() else ROOT / args.economy_report)
    hybrid = load(args.hybrid_report if args.hybrid_report.is_absolute() else ROOT / args.hybrid_report)

    donor_lines: list[str] = []
    if DONOR_SCENARIO.is_file():
        donor_lines = [x.strip() for x in DONOR_SCENARIO.read_text(encoding="utf-8").splitlines() if x.strip()]

    manifest: dict[str, Any] = {
        "schema": "cinematic_injection_manifest_v1",
        "generated_at_utc": now_utc(),
        "send_gate": "HOLD",
        "promotion": "infra_only",
        "donor_pack_root": str(CLIP_DONOR),
        "donor_scenario_file": str(DONOR_SCENARIO),
        "donor_scenario_lines_head": donor_lines[:3],
        "economy": {
            "report_json": str(args.economy_report),
            "scenario_file": economy.get("scenario_file"),
            "scenario_aligned": economy.get("scenario_aligned", True),
            "master_mp4": (economy.get("outputs") or {}).get("master_mp4"),
            "shots": shot_rows(economy, aligned=True),
        },
        "hybrid": {
            "report_json": str(args.hybrid_report),
            "scenario_file": hybrid.get("scenario_file"),
            "scenario_aligned": hybrid.get("scenario_aligned", False),
            "donor_scenario_file": hybrid.get("donor_scenario_file") or str(DONOR_SCENARIO),
            "master_mp4": (hybrid.get("outputs") or {}).get("master_mp4"),
            "shots": shot_rows(hybrid, aligned=False),
            "disclaimer": "Hero slots may reuse pre-paid Veo clips from sample_v1; not companion-human identity proof.",
        },
        "reproduce_cmd": "py scripts/cinematic/run_auditable_cinematic_free_bundle_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
