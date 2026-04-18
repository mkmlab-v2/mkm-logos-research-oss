# -*- coding: utf-8 -*-
"""CLI: global birth (UTC + IANA or local civil + IANA) → PerfectManseryeok four pillars JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.saju_birth_resolver_v1 import (  # noqa: E402
    resolve_from_local_civil,
    resolve_from_utc_instant,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Global saju pillars via IANA-aware birth resolution.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--utc-instant", type=str, metavar="ISO", help="Birth instant UTC (e.g. 1992-03-12T17:00:00Z)")
    g.add_argument("--local", nargs=6, type=int, metavar=("Y", "M", "D", "h", "m", "s"), help="Local civil clock")
    ap.add_argument("--iana-tz", required=True, help="IANA timezone (e.g. Asia/Seoul, America/New_York)")
    ap.add_argument("--dst-fold", type=int, default=0, choices=(0, 1), help="Only with --local: DST repeated hour fold")
    ap.add_argument("--is-male", action="store_true", default=False)
    ap.add_argument("--compact", action="store_true", help="Single-line JSON")
    args = ap.parse_args()

    if args.utc_instant:
        res = resolve_from_utc_instant(args.utc_instant, args.iana_tz)
    else:
        y, m, d, h, mi, s = args.local
        res = resolve_from_local_civil(y, m, d, h, mi, s, args.iana_tz, dst_fold=args.dst_fold)

    eng = PerfectManseryeok()
    full = eng.calculate_full_saju_perfect(
        res.engine_year,
        res.engine_month,
        res.engine_day,
        res.engine_hour,
        is_solar=True,
        is_male=args.is_male,
    )

    out = {
        "schema": "saju_global_birth_result_v1",
        "version": "1.0.0",
        "resolution": {
            "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "iana_tz": res.iana_tz,
            "local_iso": res.local_datetime.isoformat(),
            "engine_inputs": {
                "year": res.engine_year,
                "month": res.engine_month,
                "day": res.engine_day,
                "hour": res.engine_hour,
            },
            "warnings": list(res.warnings),
            "meta": res.meta,
        },
        "full_saju": full,
    }
    if args.compact:
        print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
