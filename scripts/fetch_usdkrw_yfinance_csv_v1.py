#!/usr/bin/env python3
"""Fetch USD/KRW daily CSV (yfinance) for hero board slot [HYPO]."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "research/market_data/usdkrw_daily_external_yf.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--days", type=int, default=120)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed", file=sys.stderr)
        return 2

    end = datetime.now(timezone.utc).date() + timedelta(days=1)
    start = end - timedelta(days=max(args.days, 30))
    ticker = yf.Ticker("KRW=X")
    hist = ticker.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=False)
    if hist is None or hist.empty:
        print("empty history", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Close", "Open", "High", "Low", "Volume"])
        for idx, row in hist.iterrows():
            dk = idx.strftime("%Y-%m-%d")
            w.writerow([dk, float(row["Close"]), float(row["Open"]), float(row["High"]), float(row["Low"]), int(row.get("Volume") or 0)])
    print(f"WROTE: {args.output} rows={len(hist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
