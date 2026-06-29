#!/usr/bin/env python3
"""Download PHLX Semiconductor Index (^SOX) daily OHLCV via yfinance — research SSOT only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "research" / "market_data" / "sox_daily_external_yf.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="^SOX", help="Yahoo ticker (default: ^SOX PHLX Semiconductor)")
    ap.add_argument("--period", default="5y")
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as e:
        print("pip install pandas yfinance", file=sys.stderr)
        raise SystemExit(2) from e

    df = yf.download(args.symbol, period=args.period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise SystemExit(f"no rows for {args.symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index()
    out_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for c in out_cols:
        if c not in df.columns:
            raise SystemExit(f"missing {c}")
    out = df[out_cols].copy()
    out["Date"] = out["Date"].astype(str).str.slice(0, 10)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(str(args.output.resolve()), len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
