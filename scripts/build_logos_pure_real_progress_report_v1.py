#!/usr/bin/env python3
"""Build daily progress report toward pure-real unique-day checkpoint."""

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
DEFAULT_OUT = ART / "logos_pure_real_progress_report_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real progress report.")
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--plan-json", type=Path, default=DEFAULT_PLAN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--target-days", type=int, default=30)
    ap.add_argument("--remaining-days", type=int, default=5)
    args = ap.parse_args()

    meta = _load_json(args.meta_json)
    _ = _load_json(args.plan_json) if args.plan_json.exists() else {}

    current = int(meta.get("output_non_synthetic_unique_days") or 0)
    target = int(args.target_days)
    remaining = max(1, int(args.remaining_days))
    gap = max(0, target - current)
    needed_per_day = math.ceil(gap / remaining) if gap > 0 else 0

    if gap == 0:
        status = "PASS_TARGET_REACHED"
    elif needed_per_day <= 2:
        status = "WARN_ON_TRACK_IF_DAILY_TARGET_MET"
    else:
        status = "FAIL_OFF_TRACK_NEED_HIGH_DAILY_INTAKE"

    out = {
        "schema": "logos_pure_real_progress_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "checkpoint": {
            "target_unique_days": target,
            "current_unique_days": current,
            "gap_unique_days": gap,
            "remaining_days": remaining,
            "required_new_unique_days_per_day": needed_per_day,
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
                "required_new_unique_days_per_day": needed_per_day,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

