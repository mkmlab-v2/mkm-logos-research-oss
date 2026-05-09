#!/usr/bin/env python3
"""Build a 7-day execution table for pure-real intake operations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROGRESS = ART / "logos_pure_real_progress_report_latest.json"
DEFAULT_MIN_INTAKE = ART / "logos_pure_real_minimum_intake_plan_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_7day_execution_table_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iso_date_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 7-day pure-real execution table.")
    ap.add_argument("--progress-json", type=Path, default=DEFAULT_PROGRESS)
    ap.add_argument("--minimum-intake-json", type=Path, default=DEFAULT_MIN_INTAKE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    progress = _load_json(args.progress_json)
    intake = _load_json(args.minimum_intake_json)

    checkpoint = progress.get("checkpoint") or {}
    intake_rec = intake.get("recommended_daily_minimum") or {}

    current_unique_days = int(checkpoint.get("current_unique_days") or 0)
    target_unique_days = int(checkpoint.get("target_unique_days") or 30)
    gap_unique_days = int(checkpoint.get("gap_unique_days") or max(0, target_unique_days - current_unique_days))

    daily_unique_target = int(
        intake_rec.get("required_new_unique_days_per_day")
        or checkpoint.get("required_new_unique_days_per_day")
        or 0
    )
    daily_source_days_target = int(intake_rec.get("required_new_source_days_per_day") or daily_unique_target)
    daily_source_rows_target = int(intake_rec.get("required_new_source_rows_per_day") or daily_source_days_target)

    start = _iso_date_today_utc()
    rows: list[dict[str, Any]] = []
    cumulative_target_unique = current_unique_days
    remaining_gap = gap_unique_days
    for i in range(max(1, int(args.days))):
        day_label = f"D+{i}"
        date_utc = (start + timedelta(days=i)).date().isoformat()
        planned_new_unique_days = min(daily_unique_target, max(0, remaining_gap))
        cumulative_target_unique += planned_new_unique_days
        remaining_gap = max(0, target_unique_days - cumulative_target_unique)
        rows.append(
            {
                "day_label": day_label,
                "date_utc": date_utc,
                "planned_new_unique_days": int(planned_new_unique_days),
                "planned_source_days": int(daily_source_days_target),
                "planned_source_rows": int(daily_source_rows_target),
                "cumulative_target_unique_days": int(cumulative_target_unique),
                "remaining_gap_after_day": int(remaining_gap),
            }
        )

    status = "PASS_TARGET_REACHED" if gap_unique_days == 0 else "EXECUTION_REQUIRED"
    out = {
        "schema": "logos_pure_real_7day_execution_table_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "checkpoint": {
            "current_unique_days": int(current_unique_days),
            "target_unique_days": int(target_unique_days),
            "gap_unique_days": int(gap_unique_days),
        },
        "daily_targets": {
            "new_unique_days_per_day": int(daily_unique_target),
            "source_days_per_day": int(daily_source_days_target),
            "source_rows_per_day": int(daily_source_rows_target),
        },
        "execution_table": rows,
        "status": status,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "days": len(rows),
                "daily_source_rows_per_day": daily_source_rows_target,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

