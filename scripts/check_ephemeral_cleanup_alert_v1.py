#!/usr/bin/env python3
"""Check cleanup summary and emit anomaly alerts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List


DEFAULT_SUMMARY_PATH = "docs/final/artifacts/ephemeral_cleanup_summary_latest.json"
DEFAULT_ALERT_LOG = "reports/ephemeral_cleanup_alerts.jsonl"
DEFAULT_ALERT_JSON = "docs/final/artifacts/ephemeral_cleanup_alert_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ephemeral cleanup anomaly alerts.")
    parser.add_argument("--summary-path", default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--alert-log-path", default=DEFAULT_ALERT_LOG)
    parser.add_argument("--alert-out", default=DEFAULT_ALERT_JSON)
    parser.add_argument("--deleted-count-warn", type=int, default=80)
    parser.add_argument("--deleted-bytes-warn", type=int, default=500_000_000)  # 500MB
    parser.add_argument("--fail-on-alert", action="store_true")
    args = parser.parse_args()

    root = Path(".").resolve()
    summary_path = root / args.summary_path
    now = datetime.now(timezone.utc).isoformat()

    if not summary_path.exists():
        payload = {
            "schema": "ephemeral_cleanup_alert_v1",
            "generated_at_utc": now,
            "status": "WARN",
            "reasons": ["missing_summary_file"],
            "summary_path": args.summary_path,
        }
    else:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        reasons: List[str] = []
        deleted_count = int(summary.get("deleted_count", 0))
        deleted_bytes = int(summary.get("deleted_bytes", 0))
        error_count = int(summary.get("error_count", 0))

        if error_count > 0:
            reasons.append("cleanup_error_count_positive")
        if deleted_count >= args.deleted_count_warn:
            reasons.append("deleted_count_spike")
        if deleted_bytes >= args.deleted_bytes_warn:
            reasons.append("deleted_bytes_spike")

        payload = {
            "schema": "ephemeral_cleanup_alert_v1",
            "generated_at_utc": now,
            "status": "ALERT" if reasons else "OK",
            "reasons": reasons,
            "summary_path": args.summary_path,
            "deleted_count": deleted_count,
            "deleted_bytes": deleted_bytes,
            "error_count": error_count,
            "thresholds": {
                "deleted_count_warn": args.deleted_count_warn,
                "deleted_bytes_warn": args.deleted_bytes_warn,
            },
        }

    out_path = root / args.alert_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    alert_log = root / args.alert_log_path
    alert_log.parent.mkdir(parents=True, exist_ok=True)
    with alert_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"[ok] alert report: {args.alert_out}")
    print(f"[ok] status: {payload['status']}")
    if payload["status"] == "ALERT" and args.fail_on_alert:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
