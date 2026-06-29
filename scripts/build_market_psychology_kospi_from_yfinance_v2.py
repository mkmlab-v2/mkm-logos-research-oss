#!/usr/bin/env python3
"""Build market_psychology v2 CSV (extended OHLC features, B-track).

Requires: pip install yfinance pandas
Output: data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv
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


def _rsi_series(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.rolling(period, min_periods=1).mean()
    avg_loss = loss.rolling(period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=400)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "market_sasang" / "market_psychology_kospi_from_yfinance_v2_latest.csv",
    )
    ap.add_argument("--ticker", type=str, default="^KS11")
    ns = ap.parse_args()

    try:
        import yfinance as yf
    except ImportError:
        print("Install yfinance: pip install yfinance", file=sys.stderr)
        return 2

    t = yf.Ticker(ns.ticker)
    df = t.history(period=f"{max(ns.days, 5) + 30}d", interval="1d", auto_adjust=True)
    if df.empty or len(df) < 5:
        print("No OHLCV rows from yfinance", file=sys.stderr)
        return 1
    df = df.dropna(subset=["Close", "High", "Low", "Volume"]).tail(ns.days).copy()
    if len(df) < 5:
        print("Insufficient rows after dropna", file=sys.stderr)
        return 1

    closes = df["Close"].astype(float)
    highs = df["High"].astype(float)
    lows = df["Low"].astype(float)
    vols = df["Volume"].astype(float)
    vol_ma20 = vols.rolling(20, min_periods=1).mean()
    rsi = _rsi_series(closes, 14)
    roll_max20 = closes.rolling(20, min_periods=1).max()
    ma20 = closes.rolling(20, min_periods=1).mean()
    ma60 = closes.rolling(60, min_periods=1).mean()

    rows_out: list[dict[str, str | float]] = []
    for i in range(len(df)):
        close = float(closes.iloc[i])
        prev_close = float(closes.iloc[i - 1]) if i > 0 else close
        ret_1d = close / prev_close - 1.0 if prev_close else 0.0
        j5 = max(0, i - 5)
        j20 = max(0, i - 20)
        ret_5d = close / float(closes.iloc[j5]) - 1.0 if j5 < i else ret_1d
        ret_20d = close / float(closes.iloc[j20]) - 1.0 if j20 < i else ret_1d
        rng = (float(highs.iloc[i]) - float(lows.iloc[i])) / close if close else 0.0
        vol = float(vols.iloc[i])
        vma = float(vol_ma20.iloc[i]) or vol
        vol_ratio = vol / vma if vma > 0 else 1.0
        peak = float(roll_max20.iloc[i]) or close
        drawdown_20d = (close / peak - 1.0) if peak else 0.0
        rsi_v = float(rsi.iloc[i])
        rsi_14_norm = clip01(rsi_v / 100.0)
        m20 = float(ma20.iloc[i]) or close
        m60 = float(ma60.iloc[i]) or close
        momentum_20_60 = (m20 / m60 - 1.0) if m60 else 0.0
        trend_strength = clip01(abs(momentum_20_60) * 8.0 + abs(ret_20d) * 4.0)

        greed_score = clip01(0.52 + 25.0 * ret_1d + 0.15 * max(0.0, ret_5d))
        fear_score = clip01(0.48 - 22.0 * ret_1d - 0.1 * max(0.0, -ret_5d))
        volatility_score = clip01(12.0 * rng + 0.15 * abs(ret_5d))
        panic_ratio = clip01(0.35 + 8.0 * rng - 5.0 * max(0.0, ret_1d))
        fomo_index = clip01(0.45 + 20.0 * max(0.0, ret_1d) + 0.1 * max(0.0, ret_5d))
        dispersion_score = clip01(0.4 + 0.35 * min(2.0, abs(1.0 - vol_ratio)) + 0.15 * volatility_score)

        idx = df.index[i]
        if hasattr(idx, "tz_convert"):
            ts = idx.tz_convert(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            ts = pd.Timestamp(idx).strftime("%Y-%m-%dT%H:%M:%SZ")

        rows_out.append(
            {
                "timestamp_utc": ts,
                "fear_score": round(fear_score, 4),
                "greed_score": round(greed_score, 4),
                "panic_ratio": round(panic_ratio, 4),
                "fomo_index": round(fomo_index, 4),
                "volatility_score": round(volatility_score, 4),
                "dispersion_score": round(dispersion_score, 4),
                "ret_1d": round(ret_1d, 6),
                "ret_5d": round(ret_5d, 6),
                "ret_20d": round(ret_20d, 6),
                "range_pct": round(rng, 6),
                "vol_ratio": round(vol_ratio, 4),
                "drawdown_20d": round(drawdown_20d, 6),
                "rsi_14_norm": round(rsi_14_norm, 4),
                "momentum_20_60": round(momentum_20_60, 6),
                "trend_strength": round(trend_strength, 4),
            }
        )

    out_df = pd.DataFrame(rows_out)
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(ns.out, index=False)
    print(f"WROTE: {ns.out.resolve()} rows={len(out_df)} ticker={ns.ticker} schema=v2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
