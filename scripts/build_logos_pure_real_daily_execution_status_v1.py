#!/usr/bin/env python3
"""Build daily execution status against 7-day pure-real plan."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROGRESS = ART / "logos_pure_real_progress_report_latest.json"
DEFAULT_TABLE = ART / "logos_pure_real_7day_execution_table_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_daily_execution_status_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _today_utc_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build daily execution status against 7-day table.")
    ap.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS)
    ap.add_argument("--table-json", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    progress = _load_json(args.progress_json)
    table = _load_json(args.table_json)

    checkpoint = progress.get("checkpoint") or {}
    current_unique_days = int(checkpoint.get("current_unique_days") or 0)
    target_unique_days = int(checkpoint.get("target_unique_days") or 30)
    gap_unique_days = int(checkpoint.get("gap_unique_days") or max(0, target_unique_days - current_unique_days))

    today = _today_utc_iso()
    today_plan: dict[str, Any] | None = None
    for row in (table.get("execution_table") or []):
        if str(row.get("date_utc") or "") == today:
            today_plan = row
            break
    if today_plan is None and (table.get("execution_table") or []):
        today_plan = (table.get("execution_table") or [])[0]

    planned_cumulative_today = int((today_plan or {}).get("cumulative_target_unique_days") or current_unique_days)
    planned_new_unique_today = int((today_plan or {}).get("planned_new_unique_days") or 0)
    deficit_vs_plan = max(0, planned_cumulative_today - current_unique_days)

    if gap_unique_days == 0:
        status = "PASS_TARGET_REACHED"
    elif deficit_vs_plan == 0:
        status = "ON_TRACK"
    else:
        status = "OFF_TRACK_NEED_CATCHUP"

    out = {
        "schema": "logos_pure_real_daily_execution_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "today_utc": today,
        "checkpoint": {
            "current_unique_days": current_unique_days,
            "target_unique_days": target_unique_days,
            "gap_unique_days": gap_unique_days,
        },
        "plan_today": {
            "planned_new_unique_days": planned_new_unique_today,
            "planned_cumulative_target_unique_days": planned_cumulative_today,
            "deficit_vs_plan": deficit_vs_plan,
        },
        "status": status,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "status": status,
                "deficit_vs_plan": deficit_vs_plan,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

