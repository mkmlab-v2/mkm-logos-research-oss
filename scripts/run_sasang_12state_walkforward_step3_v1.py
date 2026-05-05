#!/usr/bin/env python3
"""Step-3: Walk-forward survivability check (equity 30y, crypto 5y)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "sasang_12state_walkforward_step3_latest.json"


@dataclass(frozen=True)
class LaneCfg:
    lane: str
    symbol: str
    years: int
    fee_oneway_bps: float
    slippage_roundtrip_bps: float


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _download_daily(symbol: str, years: int) -> pd.DataFrame:
    period = f"{years}y"
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise SystemExit(f"no rows for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    df = df.reset_index()
    for c in ("Open", "High", "Low", "Close", "Volume"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Close"]).reset_index(drop=True)
    return df


def _cvar95(s: pd.Series) -> float:
    if s.empty:
        return 0.0
    q = s.quantile(0.05)
    tail = s[s <= q]
    return float(tail.mean()) if len(tail) else 0.0


def _mdd(eq: pd.Series) -> float:
    peak = eq.cummax()
    dd = (peak - eq) / peak.replace(0, 1.0)
    return float(dd.max()) if len(dd) else 0.0


def _assign_state(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = out["Close"].pct_change().fillna(0.0)
    out["ema12"] = out["Close"].ewm(span=12, adjust=False).mean()
    out["ema26"] = out["Close"].ewm(span=26, adjust=False).mean()
    out["macd"] = out["ema12"] - out["ema26"]
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["rsi14"] = 50.0
    d = out["Close"].diff()
    gain = d.clip(lower=0).rolling(14).mean()
    loss = (-d.clip(upper=0)).rolling(14).mean().replace(0, pd.NA)
    rs = gain / loss
    out["rsi14"] = pd.to_numeric(100 - (100 / (1 + rs)), errors="coerce").fillna(50.0)
    out["ma20"] = out["Close"].rolling(20).mean().bfill()
    dist = (out["Close"] - out["ma20"]).abs() / out["ma20"].replace(0, pd.NA)
    out["ma_dist_z"] = ((dist - dist.rolling(60).mean()) / dist.rolling(60).std().replace(0, pd.NA)).fillna(0.0)
    out["vol_z"] = ((out["Volume"] - out["Volume"].rolling(60).mean()) / out["Volume"].rolling(60).std().replace(0, pd.NA)).fillna(0.0)
    out["adx_proxy"] = (out["ret"].abs().rolling(14).mean() * 10000).fillna(10.0)

    stage = pd.Series("onset", index=out.index)
    stage[(out["rsi14"].ge(70) | out["rsi14"].le(30)) & out["ma_dist_z"].ge(1.0)] = "peak"
    div = ((out["Close"] > out["Close"].shift(10)) & (out["macd"] < out["macd"].shift(10))) | (
        (out["Close"] < out["Close"].shift(10)) & (out["macd"] > out["macd"].shift(10))
    )
    stage[div.fillna(False)] = "exhaustion"
    onset = (out["vol_z"] >= 1.0) & (out["adx_proxy"] >= 20.0)
    stage[onset] = "onset"

    r20 = out["Close"].pct_change(20).fillna(0.0)
    constitution = pd.Series("taeeum", index=out.index)
    constitution[(r20 > 0.05)] = "taeyang"
    constitution[(r20 > 0.015) & (r20 <= 0.05)] = "soyanga"
    constitution[r20 < -0.02] = "soeum"
    out["state_id"] = constitution + "_" + stage
    out["constitution"] = constitution
    out["stage"] = stage
    return out


def _simulate(df: pd.DataFrame, fee_oneway_bps: float, slip_roundtrip_bps: float) -> dict[str, float]:
    out = df.copy()
    fut = out["Close"].shift(-1) / out["Close"] - 1.0
    sig = ((out["constitution"].isin(["taeyang", "soyanga"])) & (out["stage"] != "exhaustion")).astype(int)
    friction = ((fee_oneway_bps * 2.0) + slip_roundtrip_bps) / 10000.0
    r = (sig * (fut - friction)).fillna(0.0)
    eq = (1.0 + r).cumprod()
    return {
        "total_return": float(eq.iloc[-1] - 1.0),
        "mdd": _mdd(eq),
        "cvar95": _cvar95(r[sig > 0]),
        "trades": int(sig.sum()),
    }


def _baseline_buy_hold(df: pd.DataFrame) -> dict[str, float]:
    r = (df["Close"].shift(-1) / df["Close"] - 1.0).fillna(0.0)
    eq = (1.0 + r).cumprod()
    return {
        "total_return": float(eq.iloc[-1] - 1.0),
        "mdd": _mdd(eq),
        "cvar95": _cvar95(r),
        "trades": int(len(df) - 1),
    }


def _walkforward(df: pd.DataFrame, lane_cfg: LaneCfg, train_years: int = 10, test_years: int = 2) -> dict[str, Any]:
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    start_year = int(df["Date"].dt.year.min())
    end_year = int(df["Date"].dt.year.max())
    rows = []
    y = start_year
    while y + train_years + test_years - 1 <= end_year:
        test_start = y + train_years
        test_end = test_start + test_years - 1
        test_df = df[(df["Date"].dt.year >= test_start) & (df["Date"].dt.year <= test_end)].copy()
        if len(test_df) < 50:
            y += test_years
            continue
        st = _assign_state(test_df)
        model = _simulate(st, lane_cfg.fee_oneway_bps, lane_cfg.slippage_roundtrip_bps)
        base = _baseline_buy_hold(test_df)
        rows.append(
            {
                "test_window": f"{test_start}-{test_end}",
                "model": model,
                "baseline_buy_hold": base,
                "mdd_delta": model["mdd"] - base["mdd"],
                "cvar95_delta": model["cvar95"] - base["cvar95"],
                "return_delta": model["total_return"] - base["total_return"],
            }
        )
        y += test_years

    if not rows:
        raise SystemExit(f"no walkforward rows for {lane_cfg.lane}")
    mdd_improve = sum(1 for r in rows if r["mdd_delta"] < 0)
    cvar_improve = sum(1 for r in rows if r["cvar95_delta"] > 0)
    return {
        "lane": lane_cfg.lane,
        "symbol": lane_cfg.symbol,
        "rows": rows,
        "summary": {
            "window_count": len(rows),
            "mdd_improved_windows": mdd_improve,
            "cvar_improved_windows": cvar_improve,
            "mdd_improved_ratio": mdd_improve / len(rows),
            "cvar_improved_ratio": cvar_improve / len(rows),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    lanes = [
        LaneCfg("equity_30y", "^KS11", 30, 1.0, 2.0),
        LaneCfg("crypto_5y", "BTC-USD", 5, 4.0, 4.0),
    ]
    lane_results = []
    for lane in lanes:
        df = _download_daily(lane.symbol, lane.years)
        lane_results.append(_walkforward(df, lane, train_years=10 if lane.years >= 20 else 3, test_years=2 if lane.years >= 20 else 1))

    out = {
        "schema": "sasang_12state_walkforward_step3_v1",
        "generated_at_utc": _now(),
        "lane_results": lane_results,
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "note": "Step-3 walkforward evidence for survivability focus (MDD/CVaR).",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
