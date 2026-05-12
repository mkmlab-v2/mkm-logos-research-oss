#!/usr/bin/env python3
"""Expanding-window sklearn classifier for BTC direction (research-only).

Each eval_date t uses only rows j < t for (features[j], label[j]) where label[j] is the
forward direction from j over horizon_days (same convention as kNN generator).

Outputs schema compatible with run_prophecy_btc_event_conditioned_label_sweep_v1.py.
"""
from __future__ import annotations

import os

# Reduce thread probing issues on some Windows hosts before importing sklearn.
os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import csv
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.naive_bayes import GaussianNB
except ImportError:  # lazy error in main
    LogisticRegression = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"


def _rel_to_root(p: Path) -> str:
    rp = Path(p).resolve()
    try:
        return str(rp.relative_to(ROOT))
    except ValueError:
        return str(rp)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_per_date_direction_sklearn_wf_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_prices(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            d = str(r.get("Date") or "")[:10]
            raw = str(r.get("Close") or "").strip()
            if not d or not raw:
                continue
            try:
                rows.append((d, float(raw)))
            except ValueError:
                continue
    rows.sort(key=lambda x: x[0])
    return rows


def _load_close_map(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            d = str(r.get("Date") or "")[:10]
            raw = str(r.get("Close") or "").strip()
            if not d or not raw:
                continue
            try:
                out[d] = float(raw)
            except ValueError:
                continue
    return out


def _align_series_by_dates(dates: list[str], close_map: dict[str, float]) -> list[float]:
    """Last-known carry for missing dates (same convention as cross-asset scripts)."""
    last = 0.0
    out: list[float] = []
    for d in dates:
        c = close_map.get(d)
        if c is not None and c > 0:
            last = float(c)
        out.append(last)
    return out


def _mean_abs_return(closes: list[float], i: int, k: int) -> float:
    if i < k:
        return 0.0
    vals: list[float] = []
    for j in range(i - k + 1, i + 1):
        c0 = closes[j - 1]
        c1 = closes[j]
        if c0 != 0:
            vals.append(abs((c1 - c0) / c0))
    return (sum(vals) / len(vals)) if vals else 0.0


def _ret(closes: list[float], i: int, lag: int) -> float:
    if i < lag:
        return 0.0
    c0 = closes[i - lag]
    c1 = closes[i - 1]
    if c0 == 0:
        return 0.0
    return (c1 - c0) / c0


def _rsi14_scaled(closes: list[float], i: int) -> float:
    """RSI(14) from price changes ending at bar i-1; returns ~0..1 (0.5 = neutral). Research-only."""
    period = 14
    if i < period + 1:
        return 0.5
    gains = 0.0
    losses = 0.0
    for j in range(i - period, i):
        d = closes[j] - closes[j - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_g = gains / period
    avg_l = losses / period
    if avg_l == 0.0:
        return 1.0 if avg_g > 0 else 0.5
    rs = avg_g / avg_l
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return max(0.0, min(1.0, rsi / 100.0))


def _build_features(
    closes: list[float],
    aux_series: Sequence[list[float]] | None = None,
    *,
    append_rsi14: bool = False,
) -> list[list[float]]:
    """BTC momentum/vol/MA features; optional RSI14; optional aligned aux closes, 3 feats each."""
    aux_list = list(aux_series) if aux_series else []
    rsi_extra = 1 if append_rsi14 else 0
    extra = 3 * len(aux_list) + rsi_extra
    dim = 9 + extra
    n = len(closes)
    feats: list[list[float]] = []
    for i in range(n):
        if i < 25:
            feats.append([0.0] * dim)
            continue
        r1 = _ret(closes, i, 1)
        r3 = _ret(closes, i, 3)
        r5 = _ret(closes, i, 5)
        r10 = _ret(closes, i, 10)
        r20 = _ret(closes, i, 20)
        v5 = _mean_abs_return(closes, i, 5)
        v10 = _mean_abs_return(closes, i, 10)
        ma50 = sum(closes[i - 50 : i]) / 50.0 if i >= 50 else closes[i]
        ma_ratio = (closes[i - 1] / ma50 - 1.0) if ma50 != 0 else 0.0
        row = [r1, r3, r5, r10, r20, v5, v10, ma_ratio, r10 - r3]
        if append_rsi14:
            row.append(_rsi14_scaled(closes, i))
        for aux in aux_list:
            row.extend(
                [
                    _ret(aux, i, 1),
                    _ret(aux, i, 5),
                    _mean_abs_return(aux, i, 10),
                ]
            )
        feats.append(row)
    return feats


def _label_future(closes: list[float], i: int, horizon: int, neutral_bps: float) -> str:
    j = i + horizon
    if j >= len(closes):
        return "neutral"
    c0 = closes[i]
    c1 = closes[j]
    if c0 == 0:
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


def _fit_predict(
    clf_name: str,
    X: np.ndarray,
    y: np.ndarray,
    xi: np.ndarray,
    *,
    hgb_max_iter: int,
) -> int:
    if LogisticRegression is None:
        raise SystemExit("sklearn required: pip install scikit-learn")

    if clf_name == "hgb":
        clf = HistGradientBoostingClassifier(
            max_depth=4,
            max_iter=int(hgb_max_iter),
            learning_rate=0.1,
            random_state=42,
            class_weight="balanced",
            max_leaf_nodes=40,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            clf.fit(X, y)
        return int(clf.predict(xi)[0])

    if clf_name == "rf":
        clf = RandomForestClassifier(
            n_estimators=90,
            max_depth=8,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=1,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            clf.fit(X, y)
        return int(clf.predict(xi)[0])

    if clf_name == "nb":
        clf = GaussianNB()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            clf.fit(X, y)
        return int(clf.predict(xi)[0])

    clf = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "lr",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clf.fit(X, y)
    return int(clf.predict(xi)[0])


def main() -> int:
    ap = argparse.ArgumentParser(description="BTC per-date sklearn walk-forward direction source.")
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--horizon-days", type=int, default=2)
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--train-min", type=int, default=320)
    ap.add_argument("--max-train-rows", type=int, default=1800, help="Rolling history cap for speed.")
    ap.add_argument(
        "--classifier",
        choices=("lr", "hgb", "rf", "nb"),
        default="lr",
        help="lr=logistic+scaler; hgb=HistGradientBoostingClassifier; rf=RandomForestClassifier; nb=GaussianNB.",
    )
    ap.add_argument(
        "--hgb-max-iter",
        type=int,
        default=100,
        help="For --classifier hgb: max boosting iterations (lower = faster).",
    )
    ap.add_argument(
        "--vix-csv",
        type=Path,
        default=None,
        help="Optional YFinance-style CSV (Date,Close). When set, appends r1/r5/vol10 on that series.",
    )
    ap.add_argument(
        "--kospi-csv",
        type=Path,
        default=None,
        help="Optional YFinance-style CSV (Date,Close). Same 3 features as --vix-csv; can combine.",
    )
    ap.add_argument(
        "--append-rsi14",
        action="store_true",
        help="Append one column: RSI(14) scaled to ~0..1 from closes through bar i-1.",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    btc_path = args.btc_csv if args.btc_csv.is_absolute() else (ROOT / args.btc_csv)
    prices = _load_prices(btc_path)
    dates = [d for d, _ in prices]
    closes = [c for _, c in prices]
    aux_blocks: list[list[float]] = []
    vix_rel: str | None = None
    kospi_rel: str | None = None
    if args.vix_csv is not None:
        vix_path = args.vix_csv if args.vix_csv.is_absolute() else (ROOT / args.vix_csv)
        vix_map = _load_close_map(vix_path)
        aux_blocks.append(_align_series_by_dates(dates, vix_map))
        vix_rel = _rel_to_root(vix_path)
    if args.kospi_csv is not None:
        ko_path = args.kospi_csv if args.kospi_csv.is_absolute() else (ROOT / args.kospi_csv)
        ko_map = _load_close_map(ko_path)
        aux_blocks.append(_align_series_by_dates(dates, ko_map))
        kospi_rel = _rel_to_root(ko_path)
    feats = _build_features(
        closes,
        aux_blocks if aux_blocks else None,
        append_rsi14=bool(args.append_rsi14),
    )
    labels = [_label_future(closes, i, int(args.horizon_days), float(args.neutral_bps)) for i in range(len(closes))]

    rows: list[dict[str, Any]] = []
    for i in range(int(args.train_min), len(dates) - int(args.horizon_days)):
        lo = max(0, i - int(args.max_train_rows))
        X_list = feats[lo:i]
        y_list = labels[lo:i]
        if len(X_list) < 80:
            continue
        X = np.asarray(X_list, dtype=np.float64)
        y = _encode_y(y_list)
        if np.unique(y).size < 2:
            pred = _decode_y(int(np.bincount(y).argmax()))
            rows.append({"eval_date": dates[i], "predicted_direction": pred})
            continue

        xi = np.asarray(feats[i], dtype=np.float64).reshape(1, -1)
        pred_code = _fit_predict(
            str(args.classifier),
            X,
            y,
            xi,
            hgb_max_iter=int(args.hgb_max_iter),
        )
        pred = _decode_y(pred_code)

        rows.append({"eval_date": dates[i], "predicted_direction": pred})

    payload = {
        "schema": "btc_per_date_direction_sklearn_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "btc_csv": _rel_to_root(btc_path),
            "horizon_days": int(args.horizon_days),
            "neutral_bps": float(args.neutral_bps),
            "train_min": int(args.train_min),
            "max_train_rows": int(args.max_train_rows),
            "model": (
                "hist_gradient_boosting_balanced_sample_weight"
                if args.classifier == "hgb"
                else (
                    "random_forest_balanced_subsample"
                    if args.classifier == "rf"
                    else ("gaussian_nb" if args.classifier == "nb" else "logistic_regression_balanced_lbfgs")
                )
            ),
            "classifier": str(args.classifier),
            "hgb_max_iter": int(args.hgb_max_iter) if args.classifier == "hgb" else None,
            "vix_csv": vix_rel,
            "kospi_csv": kospi_rel,
            "append_rsi14": bool(args.append_rsi14),
            "feature_dim": 9 + (1 if args.append_rsi14 else 0) + 3 * len(aux_blocks),
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
