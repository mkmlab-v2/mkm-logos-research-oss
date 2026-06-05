#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit KRX weekday gaps in KOSPI yfinance CSV [HYPO][research_only]."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/kospi_csv_gap_audit_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _krx_weekdays(d0: date, d1: date) -> list[str]:
    out: list[str] = []
    d = d0
    while d <= d1:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _load_dates(csv_path: Path) -> set[str]:
    if not csv_path.is_file():
        return set()
    out: set[str] = set()
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("Date", ""))[:10]
            if len(dk) != 10:
                continue
            try:
                px = float(row.get("Close") or 0)
            except (TypeError, ValueError):
                continue
            if px > 0:
                out.add(dk)
    return out


def audit_gaps(
    *,
    csv_path: Path,
    window_start: str,
    window_end: str | None = None,
) -> dict[str, Any]:
    from scripts.kospi_krx_calendar_v1 import krx_trading_days, load_krx_non_trading_days

    end = window_end or date.today().isoformat()
    d0 = date.fromisoformat(window_start)
    d1 = date.fromisoformat(end)
    expected = krx_trading_days(d0, d1)
    krx_weekday_all = _krx_weekdays(d0, d1)
    holidays = load_krx_non_trading_days()
    excluded = [dk for dk in krx_weekday_all if dk in holidays]
    have = _load_dates(csv_path)
    missing = [dk for dk in expected if dk not in have]
    return {
        "schema": "kospi_csv_gap_audit_v1",
        "generated_at_utc": _utc_now(),
        "csv_path": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "window_start": window_start,
        "window_end": end,
        "n_expected_krx_weekdays": len(krx_weekday_all),
        "n_expected_krx_trading_days": len(expected),
        "krx_non_trading_excluded": excluded,
        "n_present": len([d for d in expected if d in have]),
        "missing_trading_days": missing,
        "note_ko": "expected=평일−KRX휴장(JSON). missing=실거래일 OHLCV 결측 또는 Close 무효.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--window-start", default="2026-06-01")
    ap.add_argument("--window-end", default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = audit_gaps(
        csv_path=args.csv,
        window_start=args.window_start,
        window_end=args.window_end,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} missing={len(doc['missing_trading_days'])} "
        f"present={doc['n_present']}/{doc['n_expected_krx_weekdays']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
