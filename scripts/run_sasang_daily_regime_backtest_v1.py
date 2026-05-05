#!/usr/bin/env python3
"""Daily regime backtest for Sasang indicator mapping (BTC-USD)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
MAP_JSON = ART / "sasang_daily_indicator_mapping_v1_latest.json"
OUT_JSON = ART / "sasang_daily_regime_backtest_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mdd(eq: pd.Series) -> float:
    peak = eq.cummax()
    dd = (peak - eq) / peak.replace(0, 1.0)
    return float(dd.max()) if len(dd) else 0.0


def _cvar95(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    q = r.quantile(0.05)
    t = r[r <= q]
    return float(t.mean()) if len(t) else 0.0


def _load_price(symbol: str, years: int) -> pd.DataFrame:
    df = yf.download(symbol, period=f"{years}y", interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise SystemExit(f"no rows for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    out = df.reset_index()
    for c in ("Open", "High", "Low", "Close", "Volume"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["Close"]).reset_index(drop=True)
    return out


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # ADX proxy
    tr = pd.concat(
        [
            (out["High"] - out["Low"]).abs(),
            (out["High"] - out["Close"].shift(1)).abs(),
            (out["Low"] - out["Close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    plus_dm = out["High"].diff().clip(lower=0.0)
    minus_dm = (-out["Low"].diff()).clip(lower=0.0)
    tr14 = tr.rolling(14).sum().replace(0, pd.NA)
    plus_di = 100 * (plus_dm.rolling(14).sum() / tr14)
    minus_di = 100 * (minus_dm.rolling(14).sum() / tr14)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)).fillna(0.0)
    out["adx14"] = dx.rolling(14).mean().fillna(15.0)

    # OBV + zscore
    direction = (out["Close"].diff().fillna(0.0) > 0).astype(int) - (out["Close"].diff().fillna(0.0) < 0).astype(int)
    out["obv"] = (direction * out["Volume"].fillna(0.0)).cumsum()
    obv_ma = out["obv"].rolling(20).mean()
    obv_std = out["obv"].rolling(20).std().replace(0, pd.NA)
    out["obv_z20"] = ((out["obv"] - obv_ma) / obv_std).fillna(0.0)

    # ATR zscore
    out["atr14"] = tr.rolling(14).mean().bfill()
    out["atr14_z60"] = ((out["atr14"] - out["atr14"].rolling(60).mean()) / out["atr14"].rolling(60).std().replace(0, pd.NA)).fillna(0.0)

    # Wick ratio
    body = (out["Close"] - out["Open"]).abs().replace(0, pd.NA)
    wick = ((out["High"] - out[["Open", "Close"]].max(axis=1)) + (out[["Open", "Close"]].min(axis=1) - out["Low"])).clip(lower=0.0)
    out["wick_ratio"] = (wick / body).replace([pd.NA], 0.0).fillna(0.0)
    out["wick_ratio_z20"] = ((out["wick_ratio"] - out["wick_ratio"].rolling(20).mean()) / out["wick_ratio"].rolling(20).std().replace(0, pd.NA)).fillna(0.0)

    # Bollinger width + volume z
    ma20 = out["Close"].rolling(20).mean().bfill()
    std20 = out["Close"].rolling(20).std().replace(0, pd.NA).bfill()
    upper = ma20 + 2.0 * std20
    lower = ma20 - 2.0 * std20
    out["bb_mid"] = ma20
    out["bb_width"] = ((upper - lower) / ma20.replace(0, pd.NA)).fillna(0.0)
    out["bb_width_z60"] = ((out["bb_width"] - out["bb_width"].rolling(60).mean()) / out["bb_width"].rolling(60).std().replace(0, pd.NA)).fillna(0.0)
    out["volume_z60"] = ((out["Volume"] - out["Volume"].rolling(60).mean()) / out["Volume"].rolling(60).std().replace(0, pd.NA)).fillna(0.0)

    # RSI + down-volume z
    d = out["Close"].diff()
    gain = d.clip(lower=0).rolling(14).mean()
    loss = (-d.clip(upper=0)).rolling(14).mean().replace(0, pd.NA)
    rs = gain / loss
    out["rsi14"] = pd.to_numeric(100 - (100 / (1 + rs)), errors="coerce").fillna(50.0)
    down_vol = out["Volume"].where(out["Close"].diff().fillna(0.0) < 0, 0.0)
    out["down_volume_z60"] = ((down_vol - down_vol.rolling(60).mean()) / down_vol.rolling(60).std().replace(0, pd.NA)).fillna(0.0)
    out["close_above_bb_mid"] = out["Close"] > out["bb_mid"]
    return out


def _classify(out: pd.DataFrame) -> pd.Series:
    soeum = (out["rsi14"] <= 30) & (out["down_volume_z60"] >= 0.8)
    taeyang = (out["adx14"] >= 22) & (out["obv_z20"] >= 1.0) & (out["close_above_bb_mid"])
    soyanga = (out["atr14_z60"] >= 1.0) & (out["wick_ratio_z20"] >= 0.8)
    taeeum = (out["bb_width_z60"] <= -0.8) & (out["volume_z60"] <= -0.5)
    cls = pd.Series("neutral", index=out.index)
    cls[taeeum] = "taeeum"
    cls[soyanga] = "soyanga"
    cls[taeyang] = "taeyang"
    cls[soeum] = "soeum"
    return cls


def _yearly_windows(df: pd.DataFrame) -> list[tuple[int, int]]:
    years = sorted(pd.to_datetime(df["Date"]).dt.year.unique().tolist())
    return [(y, y) for y in years if y >= years[0] + 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC-USD")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    if not MAP_JSON.is_file():
        raise SystemExit(f"missing mapping artifact: {MAP_JSON}")
    mapping = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    if mapping.get("schema") != "sasang_daily_indicator_mapping_v1":
        raise SystemExit("invalid mapping schema")

    px = _load_price(args.symbol, args.years)
    d = _enrich(px)
    d["constitution"] = _classify(d)
    ret_next = (d["Close"].shift(-1) / d["Close"] - 1.0).fillna(0.0)

    # Veto policy: hold cash in risky/noise states (soeum/soyanga)
    active = (~d["constitution"].isin(["soeum", "soyanga"])).astype(int)
    veto_r = active * ret_next
    hold_r = ret_next
    eq_veto = (1.0 + veto_r).cumprod()
    eq_hold = (1.0 + hold_r).cumprod()

    summary = {
        "veto_filter": {
            "total_return": float(eq_veto.iloc[-1] - 1.0),
            "mdd": _mdd(eq_veto),
            "cvar95": _cvar95(veto_r[active > 0]),
            "active_days": int(active.sum()),
        },
        "buy_hold": {
            "total_return": float(eq_hold.iloc[-1] - 1.0),
            "mdd": _mdd(eq_hold),
            "cvar95": _cvar95(hold_r),
            "active_days": int(len(d)),
        },
    }

    windows = []
    for y0, y1 in _yearly_windows(d):
        w = d[(pd.to_datetime(d["Date"]).dt.year >= y0) & (pd.to_datetime(d["Date"]).dt.year <= y1)].copy()
        if len(w) < 40:
            continue
        wr = (w["Close"].shift(-1) / w["Close"] - 1.0).fillna(0.0)
        wa = (~w["constitution"].isin(["soeum", "soyanga"])).astype(int)
        weq_v = (1.0 + wa * wr).cumprod()
        weq_h = (1.0 + wr).cumprod()
        windows.append(
            {
                "window": f"{y0}",
                "mdd_delta": _mdd(weq_v) - _mdd(weq_h),
                "cvar95_delta": _cvar95((wa * wr)[wa > 0]) - _cvar95(wr),
                "return_delta": float((weq_v.iloc[-1] - 1.0) - (weq_h.iloc[-1] - 1.0)),
            }
        )

    mdd_improved = sum(1 for w in windows if w["mdd_delta"] < 0)
    cvar_improved = sum(1 for w in windows if w["cvar95_delta"] > 0)

    out = {
        "schema": "sasang_daily_regime_backtest_v1",
        "generated_at_utc": _now(),
        "inputs": {"symbol": args.symbol, "years": args.years, "mapping": str(MAP_JSON).replace("\\", "/")},
        "summary": summary,
        "yearly_windows": windows,
        "yearly_improvement": {
            "window_count": len(windows),
            "mdd_improved_ratio": (mdd_improved / len(windows)) if windows else 0.0,
            "cvar_improved_ratio": (cvar_improved / len(windows)) if windows else 0.0,
        },
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
