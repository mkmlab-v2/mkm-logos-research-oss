#!/usr/bin/env python3
"""Download Brent (BZ=F) daily OHLCV via yfinance for general_prophecy resolve."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "research" / "market_data" / "brent_daily_external.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BZ=F")
    ap.add_argument("--period", default="5y")
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()
    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as e:
        raise SystemExit(2) from e
    df = yf.download(ns.symbol, period=ns.period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        return 2
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index().rename(columns={c: str(c).strip() for c in df.columns})
    out_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    out = df[out_cols].copy()
    out["Date"] = out["Date"].astype(str).str.slice(0, 10)
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(ns.output, index=False)
    print(str(ns.output.resolve()), len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
