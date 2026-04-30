#!/usr/bin/env python3
"""Run a safe dry-run alert drill for Layer1/Layer5 readiness."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRILL_READINESS = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_governance_readiness_drill_latest.json"
DRILL_ALERT = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_readiness_alert_drill_latest.json"
DRILL_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_readiness_alert_drill_summary_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=DRILL_READINESS)
    ap.add_argument("--alert-result-json", type=Path, default=DRILL_ALERT)
    ap.add_argument("--summary-json", type=Path, default=DRILL_SUMMARY)
    args = ap.parse_args()

    args.readiness_json.parent.mkdir(parents=True, exist_ok=True)
    args.readiness_json.write_text(
        json.dumps(
            {
                "schema": "layer1_layer5_governance_readiness_v1",
                "status": "HOLD",
                "reasons": ["drill_simulated_hold_state"],
                "checks": {
                    "decision": "HOLD_GATE_FAIL",
                    "required_decision": "GO_CONTROLLED",
                    "approved_count": 0,
                    "min_approved_count": 50,
                    "goldset_source_mode": "approved_only",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "send_layer1_layer5_readiness_alert_v1.py"),
            "--readiness-json",
            str(args.readiness_json),
            "--output-json",
            str(args.alert_result_json),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

    alert = json.loads(args.alert_result_json.read_text(encoding="utf-8-sig"))
    summary = {
        "schema": "layer1_layer5_readiness_alert_drill_summary_v1",
        "drill_readiness_json": str(args.readiness_json).replace("\\", "/"),
        "drill_alert_result_json": str(args.alert_result_json).replace("\\", "/"),
        "should_alert": bool(alert.get("should_alert")),
        "dispatch_result": str(alert.get("dispatch_result")),
        "drill_passed": bool(alert.get("should_alert")) and str(alert.get("dispatch_result")) == "dry_run",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "drill_passed": summary["drill_passed"], "summary_json": str(args.summary_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
