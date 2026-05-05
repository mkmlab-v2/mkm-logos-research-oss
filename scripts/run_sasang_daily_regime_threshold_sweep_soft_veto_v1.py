#!/usr/bin/env python3
"""Sweep soft-veto exposure with return floor + risk improvement gates."""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "sasang_daily_regime_threshold_sweep_soft_veto_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mdd(eq: pd.Series) -> float:
    p = eq.cummax()
    d = (p - eq) / p.replace(0, 1.0)
    return float(d.max()) if len(d) else 0.0


def _cvar95(r: pd.Series) -> float:
    if r.empty:
        return 0.0
    q = r.quantile(0.05)
    tail = r[r <= q]
    return float(tail.mean()) if len(tail) else 0.0


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
    taeyang = (d["adx14"] >= p["adx_cut"]) & (d["obv_z20"] >= p["obv_cut"]) & d["close_above_bb_mid"]
    soyanga = (d["atr14_z60"] >= p["atr_z_cut"]) & (d["wick_ratio_z20"] >= p["wick_z_cut"])
    taeeum = (d["bb_width_z60"] <= p["bbw_cut"]) & (d["volume_z60"] <= p["vol_z_cut"])
    c = pd.Series("neutral", index=d.index)
    c[taeeum] = "taeeum"
    c[soyanga] = "soyanga"
    c[taeyang] = "taeyang"
    c[soeum] = "soeum"
    return c


def _eval(d: pd.DataFrame, veto_set: set[str], p: dict[str, float], soft_exposure: float) -> dict[str, float]:
    cls = _classify(d, p)
    ret = (d["Close"].shift(-1) / d["Close"] - 1.0).fillna(0.0)
    active = pd.Series(1.0, index=d.index)
    active[cls.isin(list(veto_set))] = soft_exposure
    vr = active * ret
    br = ret
    veq = (1.0 + vr).cumprod()
    beq = (1.0 + br).cumprod()
    return {
        "veto_total_return": float(veq.iloc[-1] - 1.0),
        "buyhold_total_return": float(beq.iloc[-1] - 1.0),
        "mdd_delta": _mdd(veq) - _mdd(beq),
        "cvar95_delta": _cvar95(vr) - _cvar95(br),
        "active_ratio": float(active.mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTC-USD")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--return-floor-ratio", type=float, default=0.5, help="Require veto_return >= ratio * buyhold_return")
    ap.add_argument("--mdd-delta-max", type=float, default=0.0, help="Require mdd_delta <= this value (0 means strict improvement)")
    ap.add_argument("--cvar-delta-min", type=float, default=0.0, help="Require cvar95_delta >= this value")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    d = _features(_load(args.symbol, args.years))
    veto_sets = [
        {"soeum"},
        {"soeum", "soyanga"},
        {"soeum", "taeyang"},
        {"soeum", "soyanga", "taeyang"},
    ]
    soft_exposures = [0.2, 0.35, 0.5, 0.65, 0.8]
    grid = {
        "adx_cut": [20.0, 22.0, 24.0],
        "obv_cut": [0.8, 1.0],
        "atr_z_cut": [0.8, 1.0, 1.2],
        "wick_z_cut": [0.6, 0.8, 1.0],
        "bbw_cut": [-1.0, -0.8],
        "vol_z_cut": [-0.7, -0.5],
        "rsi_cut": [28.0, 30.0, 32.0],
        "down_vol_cut": [0.6, 0.8, 1.0],
    }
    keys = list(grid.keys())
    combos = itertools.product(*(grid[k] for k in keys))
    rows = []
    for combo in combos:
        p = {k: float(v) for k, v in zip(keys, combo)}
        for vs in veto_sets:
            for se in soft_exposures:
                m = _eval(d, vs, p, soft_exposure=se)
                pass_return = m["veto_total_return"] >= args.return_floor_ratio * m["buyhold_total_return"]
                pass_mdd = m["mdd_delta"] <= args.mdd_delta_max
                pass_cvar = m["cvar95_delta"] >= args.cvar_delta_min
                composite = (1.0 if pass_mdd else 0.0) + (1.0 if pass_cvar else 0.0) + (1.0 if pass_return else 0.0)
                rows.append(
                    {
                        "veto_set": sorted(list(vs)),
                        "soft_exposure": se,
                        "params": p,
                        **m,
                        "pass_mdd": pass_mdd,
                        "pass_cvar": pass_cvar,
                        "pass_return_floor": pass_return,
                        "composite_score": composite,
                    }
                )

    ranked = sorted(
        rows,
        key=lambda x: (
            x["composite_score"],
            -x["mdd_delta"],  # more negative mdd_delta is better
            x["cvar95_delta"],
            x["veto_total_return"],
        ),
        reverse=True,
    )
    feasible = [r for r in ranked if r["pass_mdd"] and r["pass_cvar"] and r["pass_return_floor"]]

    out = {
        "schema": "sasang_daily_regime_threshold_sweep_soft_veto_v1",
        "generated_at_utc": _now(),
        "inputs": {"symbol": args.symbol, "years": args.years, "return_floor_ratio": args.return_floor_ratio},
        "gates": {"mdd_delta_max": args.mdd_delta_max, "cvar_delta_min": args.cvar_delta_min},
        "search_space": {
            "veto_set_count": len(veto_sets),
            "soft_exposure_count": len(soft_exposures),
            "param_combo_count": len(rows) // (len(veto_sets) * len(soft_exposures)),
            "total_trials": len(rows),
        },
        "best_top20": ranked[:20],
        "feasible_top20": feasible[:20],
        "feasible_count": len(feasible),
        "best_feasible": feasible[0] if feasible else None,
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
