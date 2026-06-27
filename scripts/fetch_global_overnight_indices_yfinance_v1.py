#!/usr/bin/env python3
"""Fetch Asia/global index daily CSVs for KOSPI overnight overlay [HYPO]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "research" / "market_data"

INDEX_SPECS: list[tuple[str, str, str]] = [
    ("dow", "^DJI", "dow_daily_external_yf.csv"),
    ("sp500", "^GSPC", "sp500_daily_external_yf.csv"),
    ("nasdaq", "^IXIC", "nasdaq_daily_external_yf.csv"),
    ("nikkei225", "^N225", "nikkei225_daily_external_yf.csv"),
    ("hang_seng", "^HSI", "hang_seng_daily_external_yf.csv"),
    ("shanghai", "000001.SS", "shanghai_daily_external_yf.csv"),
]


def _fetch_one(symbol: str, out_path: Path, *, period: str) -> int:
    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as e:
        print("pip install pandas yfinance", file=sys.stderr)
        raise SystemExit(2) from e

    df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        print(f"WARN: no rows for {symbol}", file=sys.stderr)
        return 1
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index()
    out_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for c in out_cols:
        if c not in df.columns:
            print(f"WARN: missing {c} for {symbol}", file=sys.stderr)
            return 1
    frame = df[out_cols].copy()
    frame["Date"] = frame["Date"].astype(str).str.slice(0, 10)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False)
    print(str(out_path.resolve()), len(frame))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--period", default="5y")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    worst = 0
    for _id, symbol, filename in INDEX_SPECS:
        rc = _fetch_one(symbol, args.out_dir / filename, period=args.period)
        worst = max(worst, rc)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
