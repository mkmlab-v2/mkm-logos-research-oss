# -*- coding: utf-8 -*-
"""Phase B-1: Physical layer — compare two 立春 instant definitions (delta_ms only).

Reference A: Meeus-style solar longitude λ=315° (scripts/core/solar_longitude_meeus_v1.py).
Reference B: Naive anchor — Feb 4 12:00 Asia/Seoul (not KASI; placeholder for delta tracking).

Does not prove KASI equivalence; plug KASI/Swiss rows later via --reference-b-file if needed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_WS = Path(__file__).resolve().parent.parent
if str(_WS) not in sys.path:
    sys.path.insert(0, str(_WS))

from scripts.core.solar_longitude_meeus_v1 import (  # noqa: E402
    jd_ut_to_datetime_utc,
    lichun_jd_ut_for_year,
)

SCHEMA = "ephemeris_baseline_report_v1"
VERSION = "1.0.0"
EPHEMERIS_DEFINITION_ID = "lichun_sun_longitude_315deg_meeus_v1_vs_naive_kst_noon_feb4_v1"


def _lichun_meeus_utc_iso(year: int) -> str:
    jd = lichun_jd_ut_for_year(year)
    dt = jd_ut_to_datetime_utc(jd).replace(tzinfo=timezone.utc)
    return _iso_z(dt)


def _lichun_naive_noon_kst_utc_iso(year: int) -> str:
    tz = ZoneInfo("Asia/Seoul")
    dt = datetime(year, 2, 4, 12, 0, 0, tzinfo=tz).astimezone(timezone.utc)
    return _iso_z(dt)


def _parse_iso_utc(s: str) -> datetime:
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t).astimezone(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _delta_ms(a_iso: str, b_iso: str) -> int:
    da = _parse_iso_utc(a_iso)
    db = _parse_iso_utc(b_iso)
    return int(abs((da - db).total_seconds() * 1000))


def _load_reference_b_file(path: Path) -> tuple[dict[int, str], str]:
    """Returns year -> instant_utc (normalized Z), sha256 hex of file bytes."""
    raw = path.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    m: dict[int, str] = {}
    for r in data.get("rows") or []:
        y = int(r["year"])
        m[y] = _iso_z(_parse_iso_utc(str(r["instant_utc"])))
    return m, h


def main() -> int:
    ap = argparse.ArgumentParser(description="Ephemeris baseline delta report (立春).")
    ap.add_argument("--year-start", type=int, default=1950)
    ap.add_argument("--year-end", type=int, default=2050)
    ap.add_argument(
        "--threshold-ms",
        type=int,
        default=14 * 24 * 3600 * 1000,
        help="Mark pass=False if delta exceeds this (default 14 days; informational)",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=_WS / "docs/final/artifacts/ephemeris_baseline_report_latest.json",
    )
    ap.add_argument(
        "--reference-b-file",
        type=Path,
        default=None,
        help="ephemeris_reference_b_lichun_v1 JSON; per-year instant_b; missing years use naive Feb4 12:00 KST",
    )
    args = ap.parse_args()

    ref_b_map: dict[int, str] = {}
    ref_b_sha: str | None = None
    ref_b_path_str: str | None = None
    if args.reference_b_file and args.reference_b_file.exists():
        ref_b_map, ref_b_sha = _load_reference_b_file(args.reference_b_file)
        ref_b_path_str = str(args.reference_b_file.resolve())

    def_id = EPHEMERIS_DEFINITION_ID
    if ref_b_sha:
        def_id = f"lichun_meeus_v1_vs_reference_b_file_sha256_{ref_b_sha[:16]}"

    rows: list[dict[str, Any]] = []
    deltas: list[int] = []

    for year in range(args.year_start, args.year_end + 1):
        instant_a = _lichun_meeus_utc_iso(year)
        instant_b = ref_b_map.get(year) or _lichun_naive_noon_kst_utc_iso(year)
        instant_b_source = "reference_b_file" if year in ref_b_map else "naive_anchor_noon_kst_feb4"
        dms = _delta_ms(instant_a, instant_b)
        deltas.append(dms)
        rows.append(
            {
                "jieqi_code": "lichun",
                "year": year,
                "instant_a_utc": instant_a,
                "instant_b_utc": instant_b,
                "instant_b_source": instant_b_source,
                "delta_ms": dms,
                "pass": dms < args.threshold_ms,
                "threshold_ms": args.threshold_ms,
            }
        )

    sorted_d = sorted(deltas)
    p95_idx = min(len(sorted_d) - 1, int(round(0.95 * (len(sorted_d) - 1))))
    ref_b_meta: dict[str, Any] = {
        "name": "naive_anchor_noon_kst_feb4",
        "note": "Years without rows in --reference-b-file use Feb 4 12:00 KST.",
    }
    if ref_b_sha:
        ref_b_meta = {
            "name": "reference_b_file",
            "path": ref_b_path_str,
            "sha256": ref_b_sha,
            "schema": "ephemeris_reference_b_lichun_v1",
        }

    report = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ephemeris_definition_id": def_id,
        "reference_a": {
            "name": "meeus_sun_longitude_315deg_v1",
            "library_version": "internal scripts/core/solar_longitude_meeus_v1.py",
        },
        "reference_b": ref_b_meta,
        "timezone_for_display": "Asia/Seoul",
        "rows": rows,
        "summary": {
            "p95_delta_ms": float(sorted_d[p95_idx]),
            "max_delta_ms": float(max(deltas)),
            "fail_count": sum(1 for r in rows if not r["pass"]),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {args.output} p95_delta_ms={report['summary']['p95_delta_ms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
