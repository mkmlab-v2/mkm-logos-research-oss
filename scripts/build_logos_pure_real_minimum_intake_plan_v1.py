#!/usr/bin/env python3
"""Build minimum intake plan to reach pure-real unique-day checkpoint."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_META = ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json"
DEFAULT_PLAN = ART / "logos_pure_real_day30_execution_plan_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_minimum_intake_plan_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_horizon_plan(
    *,
    gap_unique_days: int,
    horizon_days: int,
    unique_day_yield_per_source_day: float,
    rows_per_source_day: int,
    safety_buffer_ratio: float,
) -> dict[str, Any]:
    required_unique_days_per_day = math.ceil(gap_unique_days / max(1, horizon_days)) if gap_unique_days > 0 else 0
    required_source_days_per_day_raw = (
        math.ceil(required_unique_days_per_day / max(0.000001, unique_day_yield_per_source_day))
        if required_unique_days_per_day > 0
        else 0
    )
    required_source_days_per_day = (
        math.ceil(required_source_days_per_day_raw * max(1.0, safety_buffer_ratio))
        if required_source_days_per_day_raw > 0
        else 0
    )
    required_source_rows_per_day = required_source_days_per_day * max(1, rows_per_source_day)
    return {
        "horizon_days": int(horizon_days),
        "required_new_unique_days_per_day": int(required_unique_days_per_day),
        "assumed_unique_day_yield_per_source_day": float(unique_day_yield_per_source_day),
        "safety_buffer_ratio": float(max(1.0, safety_buffer_ratio)),
        "required_new_source_days_per_day_base": int(required_source_days_per_day_raw),
        "required_new_source_days_per_day": int(required_source_days_per_day),
        "assumed_rows_per_source_day": int(max(1, rows_per_source_day)),
        "required_new_source_rows_per_day": int(required_source_rows_per_day),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build minimum intake plan for day30 pure-real target.")
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--target-days", type=int, default=30)
    ap.add_argument("--remaining-days", type=int, default=5)
    ap.add_argument("--rows-per-source-day", type=int, default=1)
    ap.add_argument("--unique-day-yield-per-source-day", type=float, default=0.8)
    ap.add_argument("--safety-buffer-ratio", type=float, default=1.25)
    args = ap.parse_args()

    meta = _load_json(args.meta_json)
    plan = _load_json(args.plan_json) if args.plan_json.exists() else {}

    current_unique_days = int(meta.get("output_non_synthetic_unique_days") or 0)
    target_unique_days = int(
        (plan.get("checkpoint") or {}).get("target_unique_days") or args.target_days
    )
    gap_unique_days = max(0, target_unique_days - current_unique_days)

    horizons: list[int] = []
    for opt in (plan.get("daily_collection_options") or []):
        try:
            v = int(opt.get("plan_days"))
        except Exception:
            continue
        if v > 0:
            horizons.append(v)
    if int(args.remaining_days) > 0:
        horizons.append(int(args.remaining_days))
    horizons = sorted(set(horizons)) or [5]

    minimum_intake_by_horizon = [
        _build_horizon_plan(
            gap_unique_days=gap_unique_days,
            horizon_days=h,
            unique_day_yield_per_source_day=float(args.unique_day_yield_per_source_day),
            rows_per_source_day=int(args.rows_per_source_day),
            safety_buffer_ratio=float(args.safety_buffer_ratio),
        )
        for h in horizons
    ]

    recommended = _build_horizon_plan(
        gap_unique_days=gap_unique_days,
        horizon_days=max(1, int(args.remaining_days)),
        unique_day_yield_per_source_day=float(args.unique_day_yield_per_source_day),
        rows_per_source_day=int(args.rows_per_source_day),
        safety_buffer_ratio=float(args.safety_buffer_ratio),
    )

    status = "PASS_TARGET_REACHED" if gap_unique_days == 0 else "ACTION_REQUIRED"

    out = {
        "schema": "logos_pure_real_minimum_intake_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "checkpoint": {
            "target_unique_days": int(target_unique_days),
            "current_unique_days": int(current_unique_days),
            "gap_unique_days": int(gap_unique_days),
            "remaining_days": int(max(1, args.remaining_days)),
        },
        "assumptions": {
            "unique_day_yield_per_source_day": float(args.unique_day_yield_per_source_day),
            "rows_per_source_day": int(max(1, args.rows_per_source_day)),
            "safety_buffer_ratio": float(max(1.0, args.safety_buffer_ratio)),
            "conservative_mode": bool(float(args.unique_day_yield_per_source_day) < 1.0),
        },
        "recommended_daily_minimum": recommended,
        "minimum_intake_by_horizon": minimum_intake_by_horizon,
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
                "required_new_source_days_per_day": int(recommended["required_new_source_days_per_day"]),
                "required_new_source_rows_per_day": int(recommended["required_new_source_rows_per_day"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

