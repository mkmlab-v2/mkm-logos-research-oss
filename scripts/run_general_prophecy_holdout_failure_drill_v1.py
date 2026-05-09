#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "general_prophecy_holdout_failure_drill_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return cp.returncode, cp.stdout, cp.stderr


def main() -> int:
    ap = argparse.ArgumentParser(description="Run synthetic failure drill for holdout gate/alert/failure-summary chain.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    holdout_json = ART / "general_prophecy_explainability_holdout_report_failure_drill_latest.json"
    gate_json = ART / "general_prophecy_explainability_holdout_gate_failure_drill_latest.json"
    alert_json = ART / "general_prophecy_explainability_holdout_alert_failure_drill_latest.json"
    failure_json = ART / "general_prophecy_daily_queue_failure_summary_failure_drill_latest.json"

    # 1) Synthetic failing holdout input (below ops thresholds)
    _write_json(
        holdout_json,
        {
            "schema": "general_prophecy_explainability_holdout_report_v1",
            "generated_at_utc": utc_now(),
            "holdout_core": {
                "n_questions": 8,
                "direct_match_rate": 0.62,
                "fallback_match_rate": 0.38,
                "reproducible_evidence_rate": 0.84,
                "avg_biblical_keyword_coverage": 0.22,
            },
        },
    )

    # 2) Gate should fail under ops profile
    gate_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_general_prophecy_explainability_holdout_gate_v1.py"),
        "--holdout-json",
        str(holdout_json),
        "--output-json",
        str(gate_json),
        "--profile",
        "ops",
    ]
    gate_code, gate_out, gate_err = _run(gate_cmd)
    if gate_code != 0:
        raise SystemExit(f"gate command failed unexpectedly: {gate_code}\n{gate_out}\n{gate_err}")
    gate_doc = json.loads(gate_json.read_text(encoding="utf-8-sig"))

    # 3) Alert dispatch path (dry-run) should be triggered
    alert_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "alert_general_prophecy_holdout_gate_v1.py"),
        "--gate-json",
        str(gate_json),
        "--output-json",
        str(alert_json),
        "--webhook-url",
        "https://example.invalid/webhook",
        "--dry-run",
    ]
    alert_code, alert_out, alert_err = _run(alert_cmd)
    if alert_code != 0:
        raise SystemExit(f"alert command failed unexpectedly: {alert_code}\n{alert_out}\n{alert_err}")
    alert_doc = json.loads(alert_json.read_text(encoding="utf-8-sig"))

    # 4) Simulated chain failure summary contract
    _write_json(
        failure_json,
        {
            "schema": "general_prophecy_daily_queue_failure_summary_v1",
            "ts_utc": utc_now(),
            "holdout_gate_profile": "ops",
            "failed_step": "check_explainability_holdout_gate",
            "exit_code": 2,
        },
    )
    failure_doc = json.loads(failure_json.read_text(encoding="utf-8-sig"))

    out = {
        "schema": "general_prophecy_holdout_failure_drill_v1",
        "generated_at_utc": utc_now(),
        "steps": {
            "gate": {
                "ok": gate_doc.get("decision") == "WARN_HOLDOUT_DRIFT_RISK",
                "decision": gate_doc.get("decision"),
                "failed_check_keys": [k for k, v in (gate_doc.get("checks") or {}).items() if v is False],
                "artifact": str(gate_json).replace("\\", "/"),
            },
            "alert": {
                "ok": bool(alert_doc.get("alert_needed")) and str(alert_doc.get("dispatch_result")) == "dry_run",
                "alert_needed": alert_doc.get("alert_needed"),
                "dispatch_result": alert_doc.get("dispatch_result"),
                "failed_check_keys": alert_doc.get("failed_check_keys") or [],
                "artifact": str(alert_json).replace("\\", "/"),
            },
            "failure_summary": {
                "ok": (
                    failure_doc.get("failed_step") == "check_explainability_holdout_gate"
                    and int(failure_doc.get("exit_code") or 0) == 2
                ),
                "failed_step": failure_doc.get("failed_step"),
                "exit_code": failure_doc.get("exit_code"),
                "artifact": str(failure_json).replace("\\", "/"),
            },
        },
    }
    out["all_ok"] = all(bool(v.get("ok")) for v in out["steps"].values())

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    _write_json(out_path, out)
    print(json.dumps({"ok": True, "all_ok": out["all_ok"], "out": str(out_path)}, ensure_ascii=False))
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
