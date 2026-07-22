#!/usr/bin/env python3
"""Merge weather sidecar into general_prophecy_latest — signoff required; default dry-run.

CONSTITUTION wall: calibration-lab (weather_calibration_v1 / walkforward_hist) is NOT
auto-merged. Full dump requires signoff.allow_full_calibration_lab_merge=true.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from check_weather_to_general_prophecy_merge_signoff_gate_v1 import (  # noqa: E402
    CALIBRATION_TAGS,
    DEFAULT_MAIN,
    DEFAULT_SIGNOFF,
    DEFAULT_WEATHER,
    _class_b_scorable,
    _is_calibration_lab,
    _load,
    _qids,
    evaluate,
)

DEFAULT_REPORT = ROOT / "reports/weather_to_general_prophecy_merge_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _subset_registry(weather: dict[str, Any], keep_ids: set[str]) -> dict[str, Any]:
    out = dict(weather)
    out["questions"] = [
        q
        for q in (weather.get("questions") or [])
        if isinstance(q, dict) and str(q.get("question_id") or "") in keep_ids
    ]
    out["generated_at_utc"] = _utc()
    out["git_commit_hint"] = "weather_to_gp_merge_subset_v1"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--weather-json", type=Path, default=DEFAULT_WEATHER)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_MAIN)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true", default=True, help="Default: no write (always on unless --apply).")
    ap.add_argument("--apply", action="store_true", help="Perform merge (requires gate merge_allowed).")
    args = ap.parse_args()

    dry_run = not args.apply

    for p in (args.signoff_json, args.weather_json, args.registry_json):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 2

    signoff = _load(args.signoff_json)
    weather = _load(args.weather_json)
    main = _load(args.registry_json)
    gate = evaluate(signoff=signoff, weather=weather, main=main)

    allowlist = {
        str(x)
        for x in (signoff.get("allowlist_question_ids") or [])
        if isinstance(x, str) and x.strip()
    }
    main_ids = _qids(main)
    mode = str(signoff.get("merge_mode") or "class_b_scorable_subset_only")
    allow_full = bool(signoff.get("allow_full_calibration_lab_merge"))

    if allow_full and mode in {"full_calibration_lab", "allow_full"}:
        keep = {str(q.get("question_id")) for q in (weather.get("questions") or []) if isinstance(q, dict)} - main_ids
    else:
        keep = {
            str(q.get("question_id"))
            for q in (weather.get("questions") or [])
            if isinstance(q, dict)
            and _class_b_scorable(q, allowlist)
            and str(q.get("question_id") or "") not in main_ids
            and not _is_calibration_lab(q)
        }

    report: dict[str, Any] = {
        "schema": "weather_to_general_prophecy_merge_report_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "dry_run": dry_run,
        "gate_merge_decision": gate.get("merge_decision"),
        "gate_merge_allowed": gate.get("merge_allowed"),
        "would_add": sorted(keep),
        "would_add_count": len(keep),
        "calibration_tags_blocked": sorted(CALIBRATION_TAGS),
        "track_a_promotion": False,
        "live_trading_trigger": False,
        "gating_status": "NON_GATING",
    }

    if not gate.get("merge_allowed"):
        report["ok"] = True
        report["merge_applied"] = False
        report["blocked_reason"] = gate.get("rationale")
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "ok": True,
                    "blocked": True,
                    "merge_decision": gate.get("merge_decision"),
                    "would_add_count": len(keep),
                    "report": str(args.report_json),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if dry_run:
        report["ok"] = True
        report["merge_applied"] = False
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "would_add": sorted(keep), "report": str(args.report_json)}, ensure_ascii=False))
        return 0

    if not keep:
        report["ok"] = True
        report["merge_applied"] = False
        report["note"] = "nothing_to_add"
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "merge_applied": False, "note": "nothing_to_add"}, ensure_ascii=False))
        return 0

    subset = _subset_registry(weather, keep)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        tmp_path = Path(tf.name)
        tf.write(json.dumps(subset, ensure_ascii=False, indent=2))

    before_n = len(main_ids)
    cmd = [
        sys.executable,
        str(ROOT / "scripts/generate_general_prophecy_v1.py"),
        "-i",
        str(args.registry_json),
        "-o",
        str(args.registry_json),
        "--no-default-merge",
        "--merge-from",
        str(tmp_path),
    ]
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), check=False)
        if p.returncode != 0:
            return int(p.returncode)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    after = _load(args.registry_json)
    added = sorted(_qids(after) - main_ids)
    report.update(
        {
            "ok": True,
            "merge_applied": True,
            "before_question_count": before_n,
            "after_question_count": len(_qids(after)),
            "questions_added": added,
        }
    )
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "added": added, "after_count": len(_qids(after))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
