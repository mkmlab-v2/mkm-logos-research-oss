# -*- coding: utf-8 -*-
"""B-track: session wall-clock instant → four pillars + five-element mass (v0) time series CSV.

Each row is one *calendar* session instant (default KRX-style 09:00 local), resolved with
``resolve_from_local_civil`` + ``PerfectManseryeok.calculate_full_saju_perfect``.  This reuses
the natal clock engine for that wall time; it is **not** a full 擇日/日課 school implementation.

Outputs UTF-8 CSV (optional BOM for Excel) and a small JSON sidecar with parameters + disclaimer.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manseryeok_perfect_final import PerfectManseryeok  # noqa: E402
from scripts.myeongni_lens_v1.mkm_myeongni_math import compute_quant_profile_v0  # noqa: E402
from scripts.saju_birth_resolver_v1 import resolve_from_local_civil  # noqa: E402


@dataclass(frozen=True)
class SessionPanelParams:
    date_from: date
    date_to: date
    iana_tz: str
    hour: int
    minute: int
    second: int
    calendar_mode: str  # "all" | "krx_weekdays"
    dst_fold: int


def _daterange(d0: date, d1: date) -> Iterator[date]:
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def _skip_day(d: date, mode: str) -> bool:
    if mode == "all":
        return False
    if mode == "krx_weekdays":
        return d.weekday() >= 5  # Sat/Sun
    raise ValueError("calendar_mode must be 'all' or 'krx_weekdays'")


def iter_session_rows(p: SessionPanelParams) -> Iterator[dict[str, Any]]:
    eng = PerfectManseryeok()
    for d in _daterange(p.date_from, p.date_to):
        if _skip_day(d, p.calendar_mode):
            continue
        res = resolve_from_local_civil(
            d.year,
            d.month,
            d.day,
            p.hour,
            p.minute,
            p.second,
            p.iana_tz,
            dst_fold=p.dst_fold,
        )
        full = eng.calculate_full_saju_perfect(
            res.engine_year,
            res.engine_month,
            res.engine_day,
            res.engine_hour,
            is_solar=True,
            is_male=True,
        )
        saju = full.get("saju") if isinstance(full.get("saju"), dict) else {}
        pillars = {
            "year": saju.get("year"),
            "month": saju.get("month"),
            "day": saju.get("day"),
            "hour": saju.get("hour"),
        }
        quant = compute_quant_profile_v0(
            {"pillars": pillars, "sajeong_interpolation": {}}
        )
        mass = quant.get("five_element_mass_vector_v0")
        if not isinstance(mass, dict):
            mass = {}
        yield {
            "session_local_date": d.isoformat(),
            "session_local_iso": res.local_datetime.isoformat(),
            "birth_instant_utc": res.birth_instant_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "year_pillar": str(pillars.get("year") or ""),
            "month_pillar": str(pillars.get("month") or ""),
            "day_pillar": str(pillars.get("day") or ""),
            "hour_pillar": str(pillars.get("hour") or ""),
            "elem_wood": mass.get("목", ""),
            "elem_fire": mass.get("화", ""),
            "elem_earth": mass.get("토", ""),
            "elem_metal": mass.get("금", ""),
            "elem_water": mass.get("수", ""),
            "elem_imbalance": quant.get("five_element_imbalance_entropy_0_1", ""),
            "ten_god_dominance": quant.get("ten_god_dominance_index_0_1", ""),
            "quant_status": quant.get("status", ""),
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--date-to", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--hour", type=int, default=9)
    ap.add_argument("--minute", type=int, default=0)
    ap.add_argument("--second", type=int, default=0)
    ap.add_argument(
        "--calendar-mode",
        choices=("all", "krx_weekdays"),
        default="krx_weekdays",
        help="krx_weekdays: skip Sat/Sun; all: every calendar day",
    )
    ap.add_argument("--dst-fold", type=int, default=0, choices=(0, 1))
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta-json", type=Path, default=None)
    ap.add_argument(
        "--utf8-bom",
        action="store_true",
        help="Write CSV with UTF-8 BOM for Excel on Windows",
    )
    args = ap.parse_args()

    d0 = date.fromisoformat(args.date_from)
    d1 = date.fromisoformat(args.date_to)
    if d1 < d0:
        print("date-to must be >= date-from", file=sys.stderr)
        return 2

    params = SessionPanelParams(
        date_from=d0,
        date_to=d1,
        iana_tz=args.iana_tz,
        hour=args.hour,
        minute=args.minute,
        second=args.second,
        calendar_mode=args.calendar_mode,
        dst_fold=args.dst_fold,
    )

    rows = list(iter_session_rows(params))
    fieldnames = [
        "session_local_date",
        "session_local_iso",
        "birth_instant_utc",
        "year_pillar",
        "month_pillar",
        "day_pillar",
        "hour_pillar",
        "elem_wood",
        "elem_fire",
        "elem_earth",
        "elem_metal",
        "elem_water",
        "elem_imbalance",
        "ten_god_dominance",
        "quant_status",
    ]

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    mode = "w"
    encoding = "utf-8-sig" if args.utf8_bom else "utf-8"
    with args.out_csv.open(mode, newline="", encoding=encoding) as fp:
        w = csv.DictWriter(fp, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    meta = {
        "schema": "btrack_session_instant_myeongni_panel_meta_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "row_count": len(rows),
        "params": {
            "date_from": args.date_from,
            "date_to": args.date_to,
            "iana_tz": args.iana_tz,
            "session_local_hms": [args.hour, args.minute, args.second],
            "calendar_mode": args.calendar_mode,
            "dst_fold": args.dst_fold,
        },
        "out_csv": str(args.out_csv.resolve()),
        "disclaimer_ko": (
            "세션 시각을 출생 시각과 동일 엔진으로 처리한 B-track 패널이다. "
            "擇日/日課 학파 전체를 대변하지 않으며, 지지 오행은 v0 정량 블록에서 "
            "천간·지장간 슬롯이 비어 있으면 반영이 제한될 수 있다. "
            "Track A·실매매 자동 합선 금지."
        ),
    }
    meta_path = args.out_meta_json
    if meta_path is None:
        meta_path = args.out_csv.with_suffix(".meta.json")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE rows={len(rows)} csv={args.out_csv.resolve()} meta={meta_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
