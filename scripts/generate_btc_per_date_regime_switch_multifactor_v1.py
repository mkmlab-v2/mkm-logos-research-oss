#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "research" / "market_data"
DEFAULT_BTC = MD / "btc_daily_external_yf.csv"
DEFAULT_KOSPI = MD / "kospi_daily_external_yf.csv"
DEFAULT_VIX = MD / "vix_daily_external_yf.csv"
DEFAULT_WTI = MD / "wti_daily_external_yf.csv"
DEFAULT_XLE = MD / "xle_daily_external_yf.csv"
DEFAULT_ITA = MD / "ita_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_per_date_direction_regime_switch_multifactor_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    rp = p.resolve()
    try:
        return str(rp.relative_to(ROOT))
    except ValueError:
        return str(rp)


def _load_close(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out[str(r["Date"])[:10]] = float(r["Close"])
    return out


def _ret(close: dict[str, float], dates: list[str], i: int, lag: int) -> float:
    if i < lag:
        return 0.0
    c0 = close.get(dates[i - lag], 0.0)
    c1 = close.get(dates[i - 1], 0.0)
    if c0 == 0:
        return 0.0
    return (c1 - c0) / c0


def _vol(close: dict[str, float], dates: list[str], i: int, k: int) -> float:
    if i < k:
        return 0.0
    vals: list[float] = []
    for j in range(i - k + 1, i + 1):
        c0 = close.get(dates[j - 1], 0.0)
        c1 = close.get(dates[j], 0.0)
        if c0 != 0:
            vals.append(abs((c1 - c0) / c0))
    return float(sum(vals) / len(vals)) if vals else 0.0


def _future_label(close: dict[str, float], dates: list[str], i: int, horizon: int, neutral_bps: float) -> str:
    j = i + horizon
    if j >= len(dates):
        return "neutral"
    c0 = close.get(dates[i], 0.0)
    c1 = close.get(dates[j], 0.0)
    if c0 == 0:
        return "neutral"
    r = (c1 - c0) / c0
    thr = neutral_bps / 10000.0
    if r > thr:
        return "bull"
    if r < -thr:
        return "bear"
    return "neutral"


def _enc(labels: list[str]) -> np.ndarray:
    m = {"bull": 0, "bear": 1, "neutral": 2}
    return np.array([m.get(x, 2) for x in labels], dtype=np.int64)


def _dec(v: int) -> str:
    return {0: "bull", 1: "bear", 2: "neutral"}.get(int(v), "neutral")


def _clf(c: float) -> Pipeline:
    return Pipeline(
        [
            ("s", StandardScaler()),
            ("lr", LogisticRegression(max_iter=1200, class_weight="balanced", solver="lbfgs", C=float(c))),
        ]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="BTC per-date regime-switch multifactor source.")
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--vix-csv", type=Path, default=DEFAULT_VIX)
    ap.add_argument("--wti-csv", type=Path, default=DEFAULT_WTI)
    ap.add_argument("--xle-csv", type=Path, default=DEFAULT_XLE)
    ap.add_argument("--ita-csv", type=Path, default=DEFAULT_ITA)
    ap.add_argument("--horizon-days", type=int, default=2)
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--train-min", type=int, default=320)
    ap.add_argument("--max-train-rows", type=int, default=1500)
    ap.add_argument("--vol-quantile", type=float, default=0.7)
    ap.add_argument("--c-low", type=float, default=0.8)
    ap.add_argument("--c-high", type=float, default=1.5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    btc = _load_close(args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv)
    kospi = _load_close(args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv)
    vix = _load_close(args.vix_csv if args.vix_csv.is_absolute() else ROOT / args.vix_csv)
    wti = _load_close(args.wti_csv if args.wti_csv.is_absolute() else ROOT / args.wti_csv)
    xle = _load_close(args.xle_csv if args.xle_csv.is_absolute() else ROOT / args.xle_csv)
    ita = _load_close(args.ita_csv if args.ita_csv.is_absolute() else ROOT / args.ita_csv)

    dates = sorted(set(btc.keys()) & set(kospi.keys()))
    feats: list[list[float]] = []
    vols: list[float] = []
    labels: list[str] = []

    for i in range(len(dates)):
        btc_r1 = _ret(btc, dates, i, 1)
        btc_r3 = _ret(btc, dates, i, 3)
        btc_r5 = _ret(btc, dates, i, 5)
        btc_v10 = _vol(btc, dates, i, 10)
        kospi_r1 = _ret(kospi, dates, i, 1)
        kospi_r3 = _ret(kospi, dates, i, 3)
        kospi_r5 = _ret(kospi, dates, i, 5)
        vix_r1 = _ret(vix, dates, i, 1)
        vix_r5 = _ret(vix, dates, i, 5)
        wti_r1 = _ret(wti, dates, i, 1)
        xle_r1 = _ret(xle, dates, i, 1)
        ita_r1 = _ret(ita, dates, i, 1)
        feats.append(
            [
                btc_r1,
                btc_r3,
                btc_r5,
                btc_v10,
                kospi_r1,
                kospi_r3,
                kospi_r5,
                vix_r1,
                vix_r5,
                wti_r1,
                xle_r1,
                ita_r1,
                btc_r3 - kospi_r3,
                btc_r1 - vix_r1,
            ]
        )
        vols.append(btc_v10)
        labels.append(_future_label(btc, dates, i, int(args.horizon_days), float(args.neutral_bps)))

    rows: list[dict[str, Any]] = []
    for i in range(int(args.train_min), len(dates) - int(args.horizon_days)):
        lo = max(0, i - int(args.max_train_rows))
        X = np.asarray(feats[lo:i], dtype=np.float64)
        y = _enc(labels[lo:i])
        if len(X) < 100:
            continue
        xi = np.asarray(feats[i], dtype=np.float64).reshape(1, -1)
        if np.unique(y).size < 2:
            pred = _dec(int(np.bincount(y).argmax()))
            rows.append({"eval_date": dates[i], "predicted_direction": pred})
            continue

        train_vol = np.asarray(vols[lo:i], dtype=np.float64)
        cut = float(np.quantile(train_vol, max(0.1, min(0.9, float(args.vol_quantile)))))
        mask_high = train_vol >= cut
        mask_low = ~mask_high

        # Fallback to one-model fit when a regime bucket is too small.
        if int(mask_high.sum()) < 50 or int(mask_low.sum()) < 50:
            m = _clf(c=1.0)
            m.fit(X, y)
            pred = _dec(int(m.predict(xi)[0]))
            rows.append({"eval_date": dates[i], "predicted_direction": pred})
            continue

        if vols[i] >= cut:
            m = _clf(c=float(args.c_high))
            m.fit(X[mask_high], y[mask_high])
        else:
            m = _clf(c=float(args.c_low))
            m.fit(X[mask_low], y[mask_low])
        pred = _dec(int(m.predict(xi)[0]))
        rows.append({"eval_date": dates[i], "predicted_direction": pred})

    out = {
        "schema": "btc_per_date_direction_regime_switch_multifactor_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "btc_csv": _rel(args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv),
            "kospi_csv": _rel(args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv),
            "vix_csv": _rel(args.vix_csv if args.vix_csv.is_absolute() else ROOT / args.vix_csv),
            "wti_csv": _rel(args.wti_csv if args.wti_csv.is_absolute() else ROOT / args.wti_csv),
            "xle_csv": _rel(args.xle_csv if args.xle_csv.is_absolute() else ROOT / args.xle_csv),
            "ita_csv": _rel(args.ita_csv if args.ita_csv.is_absolute() else ROOT / args.ita_csv),
            "horizon_days": int(args.horizon_days),
            "neutral_bps": float(args.neutral_bps),
            "train_min": int(args.train_min),
            "max_train_rows": int(args.max_train_rows),
            "vol_quantile": float(args.vol_quantile),
            "c_low": float(args.c_low),
            "c_high": float(args.c_high),
            "model": "regime_switch_logistic_multifactor",
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

