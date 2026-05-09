#!/usr/bin/env python3
"""Build same-day catch-up target from daily execution status."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_STATUS = ART / "logos_pure_real_daily_execution_status_latest.json"
DEFAULT_TABLE = ART / "logos_pure_real_7day_execution_table_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_catchup_target_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real same-day catch-up target.")
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--table-json", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    status_doc = _load_json(args.status_json)
    table_doc = _load_json(args.table_json)
    plan_today = status_doc.get("plan_today") or {}
    daily_targets = table_doc.get("daily_targets") or {}

    deficit = int(plan_today.get("deficit_vs_plan") or 0)
    base_rows = int(daily_targets.get("source_rows_per_day") or 0)
    base_source_days = int(daily_targets.get("source_days_per_day") or 0)
    base_unique_days = int(daily_targets.get("new_unique_days_per_day") or 0)

    recommended_extra_rows_today = max(0, deficit)
    recommended_total_rows_today = max(0, base_rows + recommended_extra_rows_today)
    recommended_total_source_days_today = max(0, base_source_days + recommended_extra_rows_today)
    recommended_total_unique_days_today = max(0, base_unique_days + deficit)

    state = str(status_doc.get("status") or "")
    if state == "PASS_TARGET_REACHED":
        action = "NO_ACTION_TARGET_ALREADY_REACHED"
    elif state == "ON_TRACK":
        action = "MAINTAIN_BASE_DAILY_TARGET"
    else:
        action = "CATCH_UP_TODAY"

    out = {
        "schema": "logos_pure_real_catchup_target_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "status_ref": {
            "today_utc": status_doc.get("today_utc"),
            "status": state,
            "deficit_vs_plan": deficit,
        },
        "base_daily_target": {
            "source_rows_per_day": base_rows,
            "source_days_per_day": base_source_days,
            "new_unique_days_per_day": base_unique_days,
        },
        "today_catchup_target": {
            "recommended_extra_rows_today": recommended_extra_rows_today,
            "recommended_total_rows_today": recommended_total_rows_today,
            "recommended_total_source_days_today": recommended_total_source_days_today,
            "recommended_total_unique_days_today": recommended_total_unique_days_today,
        },
        "action": action,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "action": action,
                "recommended_total_rows_today": recommended_total_rows_today,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

