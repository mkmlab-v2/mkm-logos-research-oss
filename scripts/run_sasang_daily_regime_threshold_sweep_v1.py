#!/usr/bin/env python3
"""Sweep daily-regime veto combinations and thresholds for survivability."""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "sasang_daily_regime_threshold_sweep_v1_latest.json"


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


def _load(symbol: str, years: int) -> pd.DataFrame:
    df = yf.download(symbol, period=f"{years}y", interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise SystemExit(f"no rows for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    out = df.reset_index()
    for c in ("Open", "High", "Low", "Close", "Volume"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=["Close"]).reset_index(drop=True)


def _features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
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

    direction = (out["Close"].diff().fillna(0.0) > 0).astype(int) - (out["Close"].diff().fillna(0.0) < 0).astype(int)
    out["obv"] = (direction * out["Volume"].fillna(0.0)).cumsum()
    out["obv_z20"] = ((out["obv"] - out["obv"].rolling(20).mean()) / out["obv"].rolling(20).std().replace(0, pd.NA)).fillna(0.0)

    out["atr14"] = tr.rolling(14).mean().bfill()
    out["atr14_z60"] = ((out["atr14"] - out["atr14"].rolling(60).mean()) / out["atr14"].rolling(60).std().replace(0, pd.NA)).fillna(0.0)

    body = (out["Close"] - out["Open"]).abs().replace(0, pd.NA)
    wick = ((out["High"] - out[["Open", "Close"]].max(axis=1)) + (out[["Open", "Close"]].min(axis=1) - out["Low"])).clip(lower=0.0)
    out["wick_ratio"] = (wick / body).replace([pd.NA], 0.0).fillna(0.0)
    out["wick_ratio_z20"] = ((out["wick_ratio"] - out["wick_ratio"].rolling(20).mean()) / out["wick_ratio"].rolling(20).std().replace(0, pd.NA)).fillna(0.0)

    ma20 = out["Close"].rolling(20).mean().bfill()
    std20 = out["Close"].rolling(20).std().replace(0, pd.NA).bfill()
    upper = ma20 + 2.0 * std20
    lower = ma20 - 2.0 * std20
    out["close_above_bb_mid"] = out["Close"] > ma20
    out["bb_width_z60"] = ((((upper - lower) / ma20.replace(0, pd.NA)) - ((upper - lower) / ma20.replace(0, pd.NA)).rolling(60).mean()) / ((upper - lower) / ma20.replace(0, pd.NA)).rolling(60).std().replace(0, pd.NA)).fillna(0.0)
    out["volume_z60"] = ((out["Volume"] - out["Volume"].rolling(60).mean()) / out["Volume"].rolling(60).std().replace(0, pd.NA)).fillna(0.0)

    d = out["Close"].diff()
    gain = d.clip(lower=0).rolling(14).mean()
    loss = (-d.clip(upper=0)).rolling(14).mean().replace(0, pd.NA)
    out["rsi14"] = pd.to_numeric(100 - (100 / (1 + gain / loss)), errors="coerce").fillna(50.0)
    down_vol = out["Volume"].where(out["Close"].diff().fillna(0.0) < 0, 0.0)
    out["down_volume_z60"] = ((down_vol - down_vol.rolling(60).mean()) / down_vol.rolling(60).std().replace(0, pd.NA)).fillna(0.0)
    return out


def _classify(d: pd.DataFrame, p: dict[str, float]) -> pd.Series:
    soeum = (d["rsi14"] <= p["rsi_cut"]) & (d["down_volume_z60"] >= p["down_vol_cut"])
    taeyang = (d["adx14"] >= p["adx_cut"]) & (d["obv_z20"] >= p["obv_cut"]) & (d["close_above_bb_mid"])
    soyanga = (d["atr14_z60"] >= p["atr_z_cut"]) & (d["wick_ratio_z20"] >= p["wick_z_cut"])
    taeeum = (d["bb_width_z60"] <= p["bbw_cut"]) & (d["volume_z60"] <= p["vol_z_cut"])
    c = pd.Series("neutral", index=d.index)
    c[taeeum] = "taeeum"
    c[soyanga] = "soyanga"
    c[taeyang] = "taeyang"
    c[soeum] = "soeum"
    return c


def _eval(d: pd.DataFrame, veto_set: set[str], p: dict[str, float]) -> dict[str, float]:
    cls = _classify(d, p)
    ret_next = (d["Close"].shift(-1) / d["Close"] - 1.0).fillna(0.0)
    active = (~cls.isin(list(veto_set))).astype(int)
    vr = active * ret_next
    br = ret_next
    veq = (1.0 + vr).cumprod()
    beq = (1.0 + br).cumprod()
    return {
        "veto_total_return": float(veq.iloc[-1] - 1.0),
        "buyhold_total_return": float(beq.iloc[-1] - 1.0),
        "mdd_delta": _mdd(veq) - _mdd(beq),
        "cvar95_delta": _cvar95(vr[active > 0]) - _cvar95(br),
        "active_ratio": float(active.mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC-USD")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    d = _features(_load(args.symbol, args.years))
    veto_sets = [
        {"soeum"},
        {"soeum", "soyanga"},
        {"soeum", "taeyang"},
        {"soeum", "soyanga", "taeyang"},
    ]
    grid = {
        "adx_cut": [20.0, 22.0, 24.0],
        "obv_cut": [0.8, 1.0],
        "atr_z_cut": [0.8, 1.0, 1.2],
        "wick_z_cut": [0.6, 0.8, 1.0],
        "bbw_cut": [-1.0, -0.8, -0.6],
        "vol_z_cut": [-0.7, -0.5, -0.3],
        "rsi_cut": [28.0, 30.0, 32.0],
        "down_vol_cut": [0.6, 0.8, 1.0],
    }

    keys = list(grid.keys())
    combos = itertools.product(*(grid[k] for k in keys))
    rows = []
    for combo in combos:
        p = {k: float(v) for k, v in zip(keys, combo)}
        for vs in veto_sets:
            m = _eval(d, vs, p)
            score = 0.0
            if m["mdd_delta"] < 0:
                score += 1.0
            if m["cvar95_delta"] > 0:
                score += 1.0
            score += max(0.0, min(1.0, (m["buyhold_total_return"] - m["veto_total_return"]) * -0.02 + 0.5))
            rows.append(
                {
                    "veto_set": sorted(list(vs)),
                    "params": p,
                    **m,
                    "score": score,
                }
            )

    ranked = sorted(rows, key=lambda x: x["score"], reverse=True)
    best = ranked[:20]
    out = {
        "schema": "sasang_daily_regime_threshold_sweep_v1",
        "generated_at_utc": _now(),
        "inputs": {"symbol": args.symbol, "years": args.years},
        "search_space": {
            "veto_set_count": len(veto_sets),
            "param_combo_count": len(rows) // len(veto_sets),
            "total_trials": len(rows),
        },
        "best_top20": best,
        "best_overall": best[0] if best else None,
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
