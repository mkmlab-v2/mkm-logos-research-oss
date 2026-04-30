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
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_VIX_CSV = ROOT / "research" / "market_data" / "vix_daily_external_yf.csv"
DEFAULT_WTI_CSV = ROOT / "research" / "market_data" / "wti_daily_external_yf.csv"
DEFAULT_XLE_CSV = ROOT / "research" / "market_data" / "xle_daily_external_yf.csv"
DEFAULT_ITA_CSV = ROOT / "research" / "market_data" / "ita_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_per_date_direction_crossasset_wf_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_to_root(p: Path) -> str:
    rp = Path(p).resolve()
    try:
        return str(rp.relative_to(ROOT))
    except ValueError:
        return str(rp)


def _load_close_map(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out[str(r["Date"])[:10]] = float(r["Close"])
    return out


def _ret(close: dict[str, float], dates: list[str], i: int, lag: int) -> float:
    if i < lag:
        return 0.0
    c0 = close.get(dates[i - lag])
    c1 = close.get(dates[i - 1])
    if not c0 or not c1 or c0 == 0:
        return 0.0
    return (c1 - c0) / c0


def _vol(close: dict[str, float], dates: list[str], i: int, k: int) -> float:
    if i < k:
        return 0.0
    vals: list[float] = []
    for j in range(i - k + 1, i + 1):
        c0 = close.get(dates[j - 1], 0.0)
        c1 = close.get(dates[j], 0.0)
        if c0:
            vals.append(abs((c1 - c0) / c0))
    return float(sum(vals) / len(vals)) if vals else 0.0


def _label_future(close: dict[str, float], dates: list[str], i: int, horizon: int, neutral_bps: float) -> str:
    j = i + horizon
    if j >= len(dates):
        return "neutral"
    c0 = close.get(dates[i], 0.0)
    c1 = close.get(dates[j], 0.0)
    if not c0:
        return "neutral"
    r = (c1 - c0) / c0
    thr = neutral_bps / 10000.0
    if r > thr:
        return "bull"
    if r < -thr:
        return "bear"
    return "neutral"


def _encode_y(labels: list[str]) -> np.ndarray:
    m = {"bull": 0, "bear": 1, "neutral": 2}
    return np.array([m.get(x, 2) for x in labels], dtype=np.int64)


def _decode_y(code: int) -> str:
    inv = {0: "bull", 1: "bear", 2: "neutral"}
    return inv.get(int(code), "neutral")


def main() -> int:
    ap = argparse.ArgumentParser(description="BTC cross-asset walkforward prediction source (BTC+KOSPI features).")
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--vix-csv", type=Path, default=DEFAULT_VIX_CSV)
    ap.add_argument("--wti-csv", type=Path, default=DEFAULT_WTI_CSV)
    ap.add_argument("--xle-csv", type=Path, default=DEFAULT_XLE_CSV)
    ap.add_argument("--ita-csv", type=Path, default=DEFAULT_ITA_CSV)
    ap.add_argument("--horizon-days", type=int, default=2)
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--train-min", type=int, default=320)
    ap.add_argument("--max-train-rows", type=int, default=1500)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    btc_path = args.btc_csv if args.btc_csv.is_absolute() else (ROOT / args.btc_csv)
    kospi_path = args.kospi_csv if args.kospi_csv.is_absolute() else (ROOT / args.kospi_csv)
    vix_path = args.vix_csv if args.vix_csv.is_absolute() else (ROOT / args.vix_csv)
    wti_path = args.wti_csv if args.wti_csv.is_absolute() else (ROOT / args.wti_csv)
    xle_path = args.xle_csv if args.xle_csv.is_absolute() else (ROOT / args.xle_csv)
    ita_path = args.ita_csv if args.ita_csv.is_absolute() else (ROOT / args.ita_csv)
    btc_close = _load_close_map(btc_path)
    kospi_close = _load_close_map(kospi_path)
    vix_close = _load_close_map(vix_path)
    wti_close = _load_close_map(wti_path)
    xle_close = _load_close_map(xle_path)
    ita_close = _load_close_map(ita_path)
    # Keep sufficient sample size: anchor dates on BTC/KOSPI overlap.
    # Other external factors can be sparse and are treated as 0.0 when missing.
    dates = sorted(set(btc_close.keys()) & set(kospi_close.keys()))

    feats: list[list[float]] = []
    labels: list[str] = []
    for i in range(len(dates)):
        btc_r1 = _ret(btc_close, dates, i, 1)
        btc_r3 = _ret(btc_close, dates, i, 3)
        btc_r5 = _ret(btc_close, dates, i, 5)
        btc_v10 = _vol(btc_close, dates, i, 10)
        kospi_r1 = _ret(kospi_close, dates, i, 1)
        kospi_r3 = _ret(kospi_close, dates, i, 3)
        kospi_r5 = _ret(kospi_close, dates, i, 5)
        kospi_v10 = _vol(kospi_close, dates, i, 10)
        vix_r1 = _ret(vix_close, dates, i, 1)
        vix_r5 = _ret(vix_close, dates, i, 5)
        wti_r1 = _ret(wti_close, dates, i, 1)
        wti_r5 = _ret(wti_close, dates, i, 5)
        xle_r1 = _ret(xle_close, dates, i, 1)
        ita_r1 = _ret(ita_close, dates, i, 1)
        feats.append(
            [
                btc_r1,
                btc_r3,
                btc_r5,
                btc_v10,
                kospi_r1,
                kospi_r3,
                kospi_r5,
                kospi_v10,
                vix_r1,
                vix_r5,
                wti_r1,
                wti_r5,
                xle_r1,
                ita_r1,
                btc_r3 - kospi_r3,
                btc_r1 - vix_r1,
            ]
        )
        labels.append(_label_future(btc_close, dates, i, int(args.horizon_days), float(args.neutral_bps)))

    rows: list[dict[str, Any]] = []
    for i in range(int(args.train_min), len(dates) - int(args.horizon_days)):
        lo = max(0, i - int(args.max_train_rows))
        X = np.asarray(feats[lo:i], dtype=np.float64)
        y = _encode_y(labels[lo:i])
        if len(X) < 80:
            continue
        if np.unique(y).size < 2:
            pred = _decode_y(int(np.bincount(y).argmax()))
        else:
            clf = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("lr", LogisticRegression(max_iter=1200, class_weight="balanced", solver="lbfgs")),
                ]
            )
            clf.fit(X, y)
            pred = _decode_y(int(clf.predict(np.asarray(feats[i], dtype=np.float64).reshape(1, -1))[0]))
        rows.append({"eval_date": dates[i], "predicted_direction": pred})

    out = {
        "schema": "btc_per_date_direction_crossasset_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "btc_csv": _rel_to_root(btc_path),
            "kospi_csv": _rel_to_root(kospi_path),
            "vix_csv": _rel_to_root(vix_path),
            "wti_csv": _rel_to_root(wti_path),
            "xle_csv": _rel_to_root(xle_path),
            "ita_csv": _rel_to_root(ita_path),
            "horizon_days": int(args.horizon_days),
            "neutral_bps": float(args.neutral_bps),
            "train_min": int(args.train_min),
            "max_train_rows": int(args.max_train_rows),
            "model": "logistic_regression_balanced_crossasset_multifactor",
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

