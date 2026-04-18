# -*- coding: utf-8 -*-
"""Populate ephemeris_reference_b_lichun_v1 rows using Swiss Ephemeris (pyswisseph).

立春 = first instant in each Gregorian year when the Sun's apparent tropical
ecliptic longitude reaches 315° (UT), computed via swe.calc_ut for the Sun.

Output is Reference B for validate_ephemeris_baseline.py (--reference-b-file).
Not KASI; definition is pinned in source_note + generator_meta.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

try:
    import swisseph as swe
except ImportError as e:
    print("Install: pip install -r scripts/requirements-manseryeok-ephemeris.txt", file=sys.stderr)
    raise SystemExit(1) from e

_JD_UNIX = 2440587.5
_SCHEMA = "ephemeris_reference_b_lichun_v1"
_LICHUN_LON = 315.0


def _jd_ut_to_datetime_utc(jd_ut: float) -> datetime:
    epoch = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return epoch + timedelta(seconds=(jd_ut - _JD_UNIX) * 86400.0)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sun_lon_tropical(jd_ut: float, flags: int) -> float:
    xx, retflag = swe.calc_ut(jd_ut, swe.SUN, flags)
    if retflag < 0:
        raise RuntimeError(swe.get_planet_error())
    return float(xx[0] % 360.0)


def _resolve_calc_flags() -> int:
    """Prefer Swiss Ephemeris files; fall back to built-in Moshier."""
    jd = swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL)
    for flg in (swe.FLG_SWIEPH, swe.FLG_MOSEPH):
        try:
            xx, retflag = swe.calc_ut(jd, swe.SUN, flg)
            if retflag >= 0 and xx:
                return int(flg)
        except Exception:
            continue
    return int(swe.FLG_MOSEPH)


def lichun_jd_ut_swe(year: int, flags: int) -> float:
    """Bisection on JD (UT) for Sun longitude >= 315° in Jan–Mar window."""
    jd_lo = swe.julday(year, 1, 1, 0.0, swe.GREG_CAL)
    jd_hi = swe.julday(year, 3, 15, 0.0, swe.GREG_CAL)
    if _sun_lon_tropical(jd_lo, flags) >= _LICHUN_LON:
        raise ValueError(f"unexpected: sun already >=315 at Jan 1, year={year}")
    if _sun_lon_tropical(jd_hi, flags) < _LICHUN_LON:
        raise ValueError(f"unexpected: sun still <315 by Mar 15, year={year}")
    lo, hi = jd_lo, jd_hi
    for _ in range(80):
        if hi - lo < 1e-9:
            break
        mid = (lo + hi) / 2.0
        if _sun_lon_tropical(mid, flags) < _LICHUN_LON:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Populate Swiss Ephemeris 立春 Reference B JSON.")
    ap.add_argument("--year-start", type=int, default=1950)
    ap.add_argument("--year-end", type=int, default=2050)
    ap.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs/final/artifacts/ephemeris_reference_b_lichun_stub_v1.json",
    )
    args = ap.parse_args()

    flags = _resolve_calc_flags()
    flag_name = "FLG_SWIEPH" if flags == swe.FLG_SWIEPH else "FLG_MOSEPH"

    rows: list[dict[str, Any]] = []
    for year in range(args.year_start, args.year_end + 1):
        jd = lichun_jd_ut_swe(year, flags)
        instant = _iso_z(_jd_ut_to_datetime_utc(jd))
        rows.append({"year": year, "instant_utc": instant})

    swe_ver = str(getattr(swe, "__version__", "unknown"))
    doc = {
        "schema": _SCHEMA,
        "version": "1.0.0",
        "source_note": (
            "Auto-generated: Sun tropical longitude 315° (立春), swe.calc_ut, UT. "
            f"Flags={flag_name}. pyswisseph={swe_ver}. "
            "Not KASI API; compare deltas in validate_ephemeris_baseline.py."
        ),
        "generator_meta": {
            "script": "scripts/populate_swiss_ephemeris_lichun.py",
            "jieqi_code": "lichun",
            "solar_longitude_deg_tropical": _LICHUN_LON,
            "pyswisseph_version": swe_ver,
            "swe_calc_flags": flag_name,
        },
        "rows": rows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {args.output} ({flag_name}, pyswisseph={swe_ver})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
