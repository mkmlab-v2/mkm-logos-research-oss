# -*- coding: utf-8 -*-
"""Build dense ganji_mapping_validate_input_v1 cohort with frozen expected_pillars.

expected_pillars are snapshots from PerfectManseryeok at generation time — regression
baseline, not independent KASI/Postella ground truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.validate_ganji_mapping import _pillars_from_full  # noqa: E402

SCHEMA = "ganji_mapping_validate_input_v1"
RULE_SET_ID = "perfect_manseryeok_v1_midnight_rollover_default"
NORM_PROFILE = "hangul_two_chars_strip_ws_v1"
DEFAULT_TZ = "Asia/Seoul"


def _parse_z(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t).astimezone(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _expected_for_instant(
    eng: PerfectManseryeok, birth_utc: datetime, tz_name: str
) -> dict[str, str]:
    tz = ZoneInfo(tz_name)
    local = birth_utc.astimezone(tz)
    full = eng.calculate_full_saju_perfect(
        local.year,
        local.month,
        local.day,
        local.hour,
        is_solar=True,
        is_male=False,
        day_rollover_policy="midnight_00",
    )
    return _pillars_from_full(full)


def _build_cases(
    eng: PerfectManseryeok,
    ref_path: Path,
) -> list[dict[str, Any]]:
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    by_year = {int(r["year"]): r["instant_utc"] for r in ref.get("rows", [])}

    cases: list[dict[str, Any]] = []

    lichun_years = (1988, 1992, 2020, 2024)
    offsets_h = (-48, -36, -24, -12, 0, 12, 24, 36, 48)
    for y in lichun_years:
        base = _parse_z(by_year[y])
        for off in offsets_h:
            dt = base + timedelta(hours=off)
            cid = f"lichun_y{y}_off{off:+d}h"
            utc = _iso_z(dt)
            exp = _expected_for_instant(eng, dt, DEFAULT_TZ)
            cases.append(
                {
                    "case_id": cid,
                    "birth_instant_utc": utc,
                    "location": {"iana_tz": DEFAULT_TZ},
                    "expected_pillars": exp,
                }
            )

    zi_dates = (
        (1992, 3, 13),
        (2000, 6, 15),
        (2024, 2, 4),
        (1988, 7, 15),
        (2012, 12, 12),
    )
    zi_hours = (23, 0, 1)
    for y, m, d in zi_dates:
        tz = ZoneInfo(DEFAULT_TZ)
        for hh in zi_hours:
            local = datetime(y, m, d, hh, 0, 0, tzinfo=tz)
            dt = local.astimezone(timezone.utc)
            cid = f"zi_y{y}{m:02d}{d:02d}_h{hh:02d}kst"
            exp = _expected_for_instant(eng, dt, DEFAULT_TZ)
            cases.append(
                {
                    "case_id": cid,
                    "birth_instant_utc": _iso_z(dt),
                    "location": {"iana_tz": DEFAULT_TZ},
                    "expected_pillars": exp,
                }
            )

    misc = (
        (1975, 8, 8, 14),
        (2010, 1, 1, 12),
        (2030, 6, 1, 9),
        (1955, 11, 11, 11),
        (1999, 12, 31, 18),
        (1987, 6, 15, 10),
        (1988, 8, 20, 16),
        (2005, 3, 2, 7),
    )
    for y, m, d, hh in misc:
        tz = ZoneInfo(DEFAULT_TZ)
        local = datetime(y, m, d, hh, 0, 0, tzinfo=tz)
        dt = local.astimezone(timezone.utc)
        cid = f"misc_y{y}{m:02d}{d:02d}_h{hh:02d}"
        exp = _expected_for_instant(eng, dt, DEFAULT_TZ)
        cases.append(
            {
                "case_id": cid,
                "birth_instant_utc": _iso_z(dt),
                "location": {"iana_tz": DEFAULT_TZ},
                "expected_pillars": exp,
            }
        )

    return cases


def main() -> int:
    ap = argparse.ArgumentParser(description="Build ganji validation cohort JSON.")
    ap.add_argument(
        "--reference-lichun",
        type=Path,
        default=_WS / "docs/final/artifacts/ephemeris_reference_b_lichun_stub_v1.json",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs/final/artifacts/ganji_mapping_validate_cohort_v1.json",
    )
    args = ap.parse_args()

    if not args.reference_lichun.exists():
        print(f"Missing Reference B file: {args.reference_lichun}", file=sys.stderr)
        return 1

    eng = PerfectManseryeok()
    cases = _build_cases(eng, args.reference_lichun)
    doc = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "rule_set_id": RULE_SET_ID,
        "normalization_profile_id": NORM_PROFILE,
        "cohort_meta": {
            "expected_derivation": "perfect_manseryeok_engine_snapshot_v1",
            "purpose": "Regression checksum — not independent KASI/Postella labels.",
            "reference_lichun_path": str(args.reference_lichun.as_posix()),
            "case_count": len(cases),
        },
        "cases": cases,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
