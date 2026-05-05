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

ROOT = Path(__file__).resolve().parent.parent


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str], env: dict[str, str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Monthly drill for pre-news shadow health alert gate (webhook disabled).")
    ap.add_argument(
        "--forced-health-json",
        type=Path,
        default=Path("docs/final/artifacts/pre_news_shadow_task_health_forced_drill_latest.json"),
    )
    ap.add_argument(
        "--drill-alert-json",
        type=Path,
        default=Path("docs/final/artifacts/pre_news_shadow_task_health_alert_drill_latest.json"),
    )
    ap.add_argument(
        "--drill-log-jsonl",
        type=Path,
        default=Path("reports/pre_news_shadow_task_health_alert_drill_log.jsonl"),
    )
    ap.add_argument(
        "--drill-report-json",
        type=Path,
        default=Path("docs/final/artifacts/pre_news_shadow_alert_drill_latest.json"),
    )
    args = ap.parse_args()

    forced_path = args.forced_health_json if args.forced_health_json.is_absolute() else ROOT / args.forced_health_json
    alert_path = args.drill_alert_json if args.drill_alert_json.is_absolute() else ROOT / args.drill_alert_json
    log_path = args.drill_log_jsonl if args.drill_log_jsonl.is_absolute() else ROOT / args.drill_log_jsonl
    report_path = args.drill_report_json if args.drill_report_json.is_absolute() else ROOT / args.drill_report_json

    forced = {
        "schema": "pre_news_shadow_task_health_v1",
        "generated_at_utc": _now(),
        "task_name": "MKM-PreNews-Shadow-Daily",
        "state": "Ready",
        "last_run_time": _now(),
        "next_run_time": _now(),
        "last_task_result": 1,
        "last_task_result_hex": "0x00000001",
        "healthy": False,
        "result_category": "NonZero",
        "note": "Monthly drill forced-unhealthy payload (webhook disabled).",
    }
    _write(forced_path, forced)

    env = dict(os.environ)
    env["MKM_PRE_NEWS_SHADOW_ALERT_WEBHOOK_URL"] = ""
    env["OPS_ALARM_WEBHOOK_URL"] = ""
    cmd = [
        sys.executable,
        "scripts/alert_pre_news_shadow_task_health_v1.py",
        "--health-json",
        str(forced_path),
        "--out-alert-json",
        str(alert_path),
        "--append-log-jsonl",
        str(log_path),
    ]
    result = _run(cmd, env=env)

    alert_obj: dict[str, Any] = {}
    if alert_path.is_file():
        alert_obj = json.loads(alert_path.read_text(encoding="utf-8-sig"))
    ok = (
        result["exit_code"] == 0
        and bool(alert_obj.get("has_alert", False))
        and str(alert_obj.get("notify_status", "")) == "skipped_no_webhook"
    )

    report = {
        "schema": "pre_news_shadow_alert_drill_v1",
        "generated_at_utc": _now(),
        "forced_health_json": str(forced_path),
        "drill_alert_json": str(alert_path),
        "drill_log_jsonl": str(log_path),
        "command_result": result,
        "alert_snapshot": {
            "has_alert": alert_obj.get("has_alert"),
            "severity": alert_obj.get("severity"),
            "notified": alert_obj.get("notified"),
            "notify_status": alert_obj.get("notify_status"),
        },
        "ok": ok,
    }
    _write(report_path, report)
    print(json.dumps({"ok": ok, "report": str(report_path)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

