#!/usr/bin/env python3
"""Build market_psychology CSV for run_sasang_dna_market_reasoning_v1 (KOSPI lane).

OHLCV-only heuristics (B-track): no news/history columns. Scores in [0,1].
Requires: pip install yfinance pandas

Each row = one trading day (yfinance ^KS11). transition_model in Sasang reasoning
needs >=2 rows; use --days 30 or more for meaningful byungjeung probabilities.
"""
from __future__ import annotations

import argparse
import sys
from datetime import timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=45, help="Trading days to fetch (default 45)")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "market_sasang" / "market_psychology_kospi_from_yfinance_latest.csv",
    )
    ap.add_argument("--ticker", type=str, default="^KS11")
    ns = ap.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("Install yfinance: pip install yfinance", file=sys.stderr)
        return 2

    t = yf.Ticker(ns.ticker)
    df = t.history(period=f"{max(ns.days, 5) + 15}d", interval="1d", auto_adjust=True)
    if df.empty or len(df) < 2:
        print("No OHLCV rows from yfinance", file=sys.stderr)
        return 1
    df = df.dropna(subset=["Close", "High", "Low", "Volume"]).tail(ns.days).copy()
    if len(df) < 2:
        print("Insufficient rows after dropna", file=sys.stderr)
        return 1

    closes = df["Close"].astype(float)
    highs = df["High"].astype(float)
    lows = df["Low"].astype(float)
    vols = df["Volume"].astype(float)
    vol_ma20 = vols.rolling(20, min_periods=1).mean()

    rows_out: list[dict[str, str | float]] = []
    for i in range(len(df)):
        close = float(closes.iloc[i])
        prev_close = float(closes.iloc[i - 1]) if i > 0 else close
        ret = close / prev_close - 1.0 if prev_close else 0.0
        rng = (float(highs.iloc[i]) - float(lows.iloc[i])) / close if close else 0.0
        vol = float(vols.iloc[i])
        vma = float(vol_ma20.iloc[i]) or vol
        vol_ratio = vol / vma if vma > 0 else 1.0
        j = i - 5
        if j >= 0:
            ret_5d = close / float(closes.iloc[j]) - 1.0
        else:
            ret_5d = ret

        greed_score = clip01(0.52 + 25.0 * ret + 0.15 * max(0.0, ret_5d))
        fear_score = clip01(0.48 - 22.0 * ret - 0.1 * max(0.0, -ret_5d))
        volatility_score = clip01(12.0 * rng + 0.15 * abs(ret_5d))
        panic_ratio = clip01(0.35 + 8.0 * rng - 5.0 * max(0.0, ret))
        fomo_index = clip01(0.45 + 20.0 * max(0.0, ret) + 0.1 * max(0.0, ret_5d))
        dispersion_score = clip01(0.4 + 0.35 * min(2.0, abs(1.0 - vol_ratio)) + 0.15 * volatility_score)

        idx = df.index[i]
        if hasattr(idx, "tz_convert"):
            ts = idx.tz_convert(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            ts = pd.Timestamp(idx).strftime("%Y-%m-%dT%H:%M:%SZ")

        rows_out.append(
            {
                "timestamp_utc": ts,
                "fear_score": round(fear_score, 3),
                "greed_score": round(greed_score, 3),
                "panic_ratio": round(panic_ratio, 3),
                "fomo_index": round(fomo_index, 3),
                "volatility_score": round(volatility_score, 3),
                "dispersion_score": round(dispersion_score, 3),
            }
        )

    out_df = pd.DataFrame(rows_out)
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(ns.out, index=False)
    print(f"WROTE: {ns.out.resolve()} rows={len(out_df)} ticker={ns.ticker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())