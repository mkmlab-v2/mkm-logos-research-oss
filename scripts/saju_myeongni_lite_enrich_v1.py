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

from scripts.build_myeongni_full_report_v1 import (  # noqa: E402
    ELEMENT_ONLY,
    _element_profile,
    _split_ganji,
    _strength_hint,
    _ten_god_profile,
)
from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.myeongri_daewoon_timeline_v1 import build_myeongri_daewoon_timeline_v1  # noqa: E402
from scripts.saju_birth_resolver_v1 import resolve_from_utc_instant  # noqa: E402


def _build_oheng_tengod_lite(pillars: dict[str, str | None]) -> dict[str, object]:
    """Visible 오행 counts + combined 십성 counts + non-clinical strength hint."""
    pillars_str = {k: str(pillars.get(k) or "") for k in ("year", "month", "day", "hour")}
    elem_profile = _element_profile(pillars_str)
    _, month_ji = _split_ganji(pillars_str.get("month"))
    day_stem, _ = _split_ganji(pillars_str.get("day"))
    day_elem = ELEMENT_ONLY.get(day_stem, "")
    counts_visible = elem_profile.get("element_counts_visible") or {}
    strength = _strength_hint(month_ji, day_elem, counts_visible)
    tg = _ten_god_profile(
        day_stem,
        list(elem_profile.get("stems") or []),
        list(elem_profile.get("hidden_stems_by_branch") or []),
    )
    surface_counts: dict[str, int] = {}
    for item in tg.get("visible_stem_ten_gods") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("ten_god") or "").strip()
        if name:
            surface_counts[name] = surface_counts.get(name, 0) + 1
    combined = tg.get("ten_god_counts_combined") if isinstance(tg.get("ten_god_counts_combined"), dict) else {}
    return {
        "oheng_visible": {
            "element_counts_visible": counts_visible,
            "dominant_element_visible": elem_profile.get("dominant_element_visible"),
            "weakest_element_visible": elem_profile.get("weakest_element_visible"),
        },
        "ten_god_lite": {
            "counts_combined_ko": combined,
            "counts_surface_ko": surface_counts,
        },
        "strength_hint": {
            "strength_label": strength.get("strength_label"),
            "note": strength.get("note"),
        },
    }


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
    pillars_out = {
        "year": saju.get("year"),
        "month": saju.get("month"),
        "day": saju.get("day"),
        "hour": saju.get("hour"),
    }
    oheng_tengod = _build_oheng_tengod_lite(pillars_out)

    out = {
        "schema": "saju_myeongni_lite_enrich_v1",
        "version": "1.1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pillars": pillars_out,
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
        "disclaimer_ko": "대운·세운·오행·십성은 엔진 Fact 참고만; 월운·용신 처방·의학 SSOT 대체 금지",
        **oheng_tengod,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
