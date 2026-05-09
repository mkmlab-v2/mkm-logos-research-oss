#!/usr/bin/env python3
"""Build weekly alert from execution gate trend log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_LOG = REPORTS / "logos_pure_real_execution_gate_trend_log.jsonl"
DEFAULT_OUT = ART / "logos_pure_real_execution_gate_weekly_alert_latest.json"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


def _parse_dt(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly execution gate alert.")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--recent-sample-size", type=int, default=3)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max(1, int(args.window_days)))
    rows = _load_jsonl(args.log_jsonl)
    in_window: list[dict[str, Any]] = []
    for r in rows:
        dt = _parse_dt(str(r.get("timestamp_utc") or ""))
        if dt is None:
            continue
        if dt >= cutoff:
            in_window.append(r)

    fail_count = sum(1 for r in in_window if str(r.get("gate_status") or "") == "FAIL_ACTION_REQUIRED")
    warn_count = sum(1 for r in in_window if str(r.get("gate_status") or "") == "WARN_CONTINUE_DAILY_EXECUTION")
    pass_count = sum(1 for r in in_window if str(r.get("gate_status") or "") == "PASS_EXECUTION_AND_DELTA_OK")
    total = len(in_window)
    legacy_alert = fail_count > 0

    recent_n = max(1, int(args.recent_sample_size))
    sorted_window = sorted(
        in_window,
        key=lambda r: str(r.get("timestamp_utc") or ""),
    )
    recent = sorted_window[-recent_n:]
    recent_fail_count = sum(1 for r in recent if str(r.get("gate_status") or "") == "FAIL_ACTION_REQUIRED")
    recent_warn_count = sum(1 for r in recent if str(r.get("gate_status") or "") == "WARN_CONTINUE_DAILY_EXECUTION")
    recent_pass_count = sum(1 for r in recent if str(r.get("gate_status") or "") == "PASS_EXECUTION_AND_DELTA_OK")
    alert = recent_fail_count > 0

    out = {
        "schema": "logos_pure_real_execution_gate_weekly_alert_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "window_days": int(max(1, args.window_days)),
        "window_record_count": total,
        "legacy_is_alert": legacy_alert,
        "recent_sample_size": recent_n,
        "recent_counts": {
            "fail_action_required": recent_fail_count,
            "warn_continue_daily_execution": recent_warn_count,
            "pass_execution_and_delta_ok": recent_pass_count,
        },
        "counts": {
            "fail_action_required": fail_count,
            "warn_continue_daily_execution": warn_count,
            "pass_execution_and_delta_ok": pass_count,
        },
        "is_alert": alert,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "window_record_count": total,
                "is_alert": alert,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

