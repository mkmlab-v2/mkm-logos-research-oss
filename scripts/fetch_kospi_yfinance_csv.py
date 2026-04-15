#!/usr/bin/env python3
"""Download KOSPI (^KS11) daily OHLCV via yfinance into research SSOT CSV path.

Writes a single-header CSV compatible with ``load_kospi_yf_rows`` (Date-first row).
Does not touch trading or promotion gates.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="^KS11", help="Yahoo Finance ticker (default KOSPI index)")
    ap.add_argument("--period", default="5y", help="yfinance period=… (ignored if --start is set)")
    ap.add_argument(
        "--start",
        default="",
        help="YYYY-MM-DD download start (inclusive). Use with long history, e.g. 1990-01-01 for ~30y+.",
    )
    ap.add_argument("--end", default="", help="Optional YYYY-MM-DD end (exclusive upper bound for yfinance).")
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="Print resolved paths only; no download")
    ns = ap.parse_args()

    if ns.dry_run:
        print("ok", ns.symbol, str(ns.output.resolve()))
        return 0

    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as e:  # pragma: no cover
        print("requires pandas and yfinance: pip install pandas yfinance", file=sys.stderr)
        raise SystemExit(2) from e

    if ns.start.strip():
        kwargs: dict = {
            "interval": "1d",
            "auto_adjust": False,
            "progress": False,
        }
        if ns.end.strip():
            df = yf.download(ns.symbol, start=ns.start.strip(), end=ns.end.strip(), **kwargs)
        else:
            df = yf.download(ns.symbol, start=ns.start.strip(), **kwargs)
    else:
        df = yf.download(ns.symbol, period=ns.period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        print(f"no rows for {ns.symbol!r}", file=sys.stderr)
        return 2
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index()
    # Normalize column names for load_kospi_yf_rows (Date-first header).
    rename = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=rename)
    if "Date" not in df.columns:
        print("expected Date column after reset_index", file=sys.stderr)
        return 2
    out_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for c in out_cols:
        if c not in df.columns:
            print(f"missing column {c!r} in download", file=sys.stderr)
            return 2
    out = df[out_cols].copy()
    out["Date"] = out["Date"].astype(str).str.slice(0, 10)

    ns.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(ns.output, index=False)
    print(str(ns.output.resolve()), len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
