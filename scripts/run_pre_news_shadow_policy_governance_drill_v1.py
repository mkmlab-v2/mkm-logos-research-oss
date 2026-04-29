#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def run(cmd: list[str], env: dict[str, str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    return {"cmd": cmd, "exit_code": cp.returncode, "stdout": cp.stdout.strip(), "stderr": cp.stderr.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Drill policy governance alert path.")
    ap.add_argument(
        "--forced-audit-summary-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_forced_drill_latest.json",
    )
    ap.add_argument(
        "--forced-alert-json",
        default="docs/final/artifacts/pre_news_shadow_policy_governance_alert_forced_drill_latest.json",
    )
    ap.add_argument(
        "--forced-alert-log-jsonl",
        default="reports/pre_news_shadow_policy_governance_alert_forced_drill_log.jsonl",
    )
    ap.add_argument(
        "--drill-report-json",
        default="docs/final/artifacts/pre_news_shadow_policy_governance_drill_latest.json",
    )
    ap.add_argument("--threshold", type=int, default=2)
    args = ap.parse_args()

    summary_path = resolve(args.forced_audit_summary_json)
    alert_path = resolve(args.forced_alert_json)
    alert_log_path = resolve(args.forced_alert_log_jsonl)
    report_path = resolve(args.drill_report_json)

    forced_summary = {
        "schema": "pre_news_shadow_stage_threshold_policy_audit_summary_v1",
        "generated_at_utc": now(),
        "window_days": 30,
        "metrics": {
            "change_count_window": max(3, int(args.threshold) + 1),
            "change_count_total": max(3, int(args.threshold) + 1),
            "latest_change_detected_at_utc": now(),
        },
        "current_policy_state": {
            "policy_version": "drill-v1",
            "approved_by": "athena-core",
            "approved_by_1": "athena-core",
            "approved_by_2": "athena-sentinel",
            "effective_from_utc": "2026-01-01T00:00:00Z",
            "policy_fingerprint_sha256": "drill",
            "has_two_person_approval": True,
        },
        "risk_summary": "MEDIUM: forced governance drill summary",
    }
    write_json(summary_path, forced_summary)

    env = dict(os.environ)
    # Drill should validate gate path without sending live alerts.
    env["MKM_PRE_NEWS_POLICY_GOVERNANCE_ALERT_WEBHOOK_URL"] = ""
    env["OPS_ALARM_WEBHOOK_URL"] = ""
    cmd = [
        sys.executable,
        "scripts/alert_pre_news_shadow_policy_governance_v1.py",
        "--audit-summary-json",
        str(summary_path),
        "--out-alert-json",
        str(alert_path),
        "--append-alert-log-jsonl",
        str(alert_log_path),
        "--change-count-threshold",
        str(max(1, int(args.threshold))),
    ]
    result = run(cmd, env=env)
    alert = read_json(alert_path)
    ok = (
        result["exit_code"] == 0
        and bool(alert.get("has_alert", False))
        and str(alert.get("severity", "")) == "warning"
    )
    drill_report = {
        "schema": "pre_news_shadow_policy_governance_drill_v1",
        "generated_at_utc": now(),
        "forced_audit_summary_json": str(summary_path),
        "forced_alert_json": str(alert_path),
        "command_result": result,
        "alert_snapshot": {
            "has_alert": alert.get("has_alert"),
            "severity": alert.get("severity"),
            "notify_status": alert.get("notify_status"),
        },
        "ok": ok,
    }
    write_json(report_path, drill_report)
    print(json.dumps({"ok": ok, "report": str(report_path)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

