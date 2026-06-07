#!/usr/bin/env python3
"""Birth instant → pillars + active daewoon + calendar-year sewoon (lite, no monthly prescription)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.myeongri_daewoon_timeline_v1 import build_myeongri_daewoon_timeline_v1  # noqa: E402
from scripts.saju_birth_resolver_v1 import resolve_from_utc_instant  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--birth-instant-utc", required=True)
    ap.add_argument("--iana-tz", required=True)
    ap.add_argument("--is-male", action="store_true", default=False)
    ap.add_argument("--as-of-utc", default=None, help="Default: now UTC")
    ap.add_argument("--sewoon-year", type=int, default=None, help="Calendar year for sewoon; default as_of year")
    args = ap.parse_args()

    res = resolve_from_utc_instant(args.birth_instant_utc, args.iana_tz)
    eng = PerfectManseryeok()
    full = eng.calculate_full_saju_perfect(
        res.engine_year,
        res.engine_month,
        res.engine_day,
        res.engine_hour,
        is_solar=True,
        is_male=args.is_male,
    )
    saju = full.get("saju") or {}
    year_pillar = str(saju.get("year") or "")
    month_pillar = str(saju.get("month") or "")

    as_of = args.as_of_utc or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    timeline = build_myeongri_daewoon_timeline_v1(
        birth_year=res.engine_year,
        birth_month=res.engine_month,
        birth_day=res.engine_day,
        birth_hour=res.engine_hour,
        month_pillar=month_pillar,
        year_gan=year_pillar[0] if year_pillar else "",
        is_male=args.is_male,
        as_of_utc=as_of,
    )
    active = timeline.get("active_cycle") or {}
    dae_pillar = active.get("pillar") or active.get("saju")

    as_of_dt = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    sewoon_year = args.sewoon_year if args.sewoon_year is not None else as_of_dt.year
    sewoon_pillar = eng.calculate_year_pillar(sewoon_year, 7, 1)

    day_pillar = str(saju.get("day") or "")
    out = {
        "schema": "saju_myeongni_lite_enrich_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pillars": {
            "year": saju.get("year"),
            "month": saju.get("month"),
            "day": saju.get("day"),
            "hour": saju.get("hour"),
        },
        "day_master_stem": day_pillar[0] if day_pillar else None,
        "daewoon_current": {
            "pillar": dae_pillar,
            "age_start": active.get("age_start"),
            "age_end": active.get("age_end"),
            "cycle": active.get("cycle"),
        }
        if active
        else None,
        "sewoon_current": {
            "calendar_year": sewoon_year,
            "pillar": sewoon_pillar,
            "note": "mid-year(7/1) year-pillar proxy; not monthly prescription",
        },
        "disclaimer_ko": "대운·세운은 엔진 Fact 참고만; 월운·처방·의학 SSOT 대체 금지",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
