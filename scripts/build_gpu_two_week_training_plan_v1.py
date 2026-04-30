#!/usr/bin/env python3
"""Build 2-week GPU/ops training schedule artifact."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "gpu_two_week_training_plan_v1_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    start = _now().date()
    days = [start + timedelta(days=i) for i in range(14)]

    plan = []
    for i, d in enumerate(days, start=1):
        if i in (1, 4, 8, 11):
            focus = "gpu_shadow_calibration"
            task = "GPU shadow score vs live outcome calibration batch"
        elif i in (2, 5, 9, 12):
            focus = "regime_threshold_retune"
            task = "Regime-specific threshold retune + stability check"
        elif i in (3, 6, 10, 13):
            focus = "rollback_drill_scoring"
            task = "Rollback drill scoring (recovery time / gate health)"
        else:
            focus = "weekly_review"
            task = "Weekly synthesis + next-iteration parameter lock"
        plan.append(
            {
                "day_index": i,
                "date_utc": _fmt(datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)),
                "focus": focus,
                "task": task,
                "required_outputs": [
                    "docs/final/artifacts/live_gpu_unified_status_dashboard_v1_latest.json"
                ],
            }
        )

    payload = {
        "schema": "gpu_two_week_training_plan_v1",
        "generated_at_utc": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "duration_days": 14,
        "tracks": [
            "gpu_shadow_calibration",
            "regime_threshold_retune",
            "rollback_drill_scoring",
        ],
        "schedule": plan,
        "constraints": {
            "no_auto_live_binding": True,
            "human_review_required_for_live_switch": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
