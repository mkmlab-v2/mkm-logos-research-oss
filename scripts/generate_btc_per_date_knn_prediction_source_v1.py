#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_per_date_direction_knn_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_prices(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append((str(r["Date"])[:10], float(r["Close"])))
    rows.sort(key=lambda x: x[0])
    return rows


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


def _build_features(prices: list[tuple[str, float]]) -> tuple[list[str], list[list[float]], list[float]]:
    dates = [d for d, _ in prices]
    closes = [c for _, c in prices]
    feats: list[list[float]] = []
    for i in range(len(prices)):
        if i < 10:
            feats.append([0.0, 0.0, 0.0, 0.0])
            continue
        c1 = closes[i - 1]
        r1 = (closes[i] - c1) / c1 if c1 != 0 else 0.0
        c3 = closes[i - 3]
        c5 = closes[i - 5]
        r3 = (closes[i - 1] - c3) / c3 if c3 != 0 else 0.0
        r5 = (closes[i - 1] - c5) / c5 if c5 != 0 else 0.0
        v10 = _mean_abs_return(closes, i, 10)
        feats.append([r1, r3, r5, v10])
    return dates, feats, closes


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


def _dist(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate per-date BTC direction source via expanding-window kNN.")
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--horizon-days", type=int, default=2)
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--k", type=int, default=25)
    ap.add_argument("--train-min", type=int, default=300)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    prices = _load_prices(args.btc_csv)
    dates, feats, closes = _build_features(prices)
    labels = [_label_future(closes, i, int(args.horizon_days), float(args.neutral_bps)) for i in range(len(closes))]

    rows: list[dict[str, Any]] = []
    for i in range(int(args.train_min), len(dates) - int(args.horizon_days)):
        q = feats[i]
        neighbors: list[tuple[float, str]] = []
        for j in range(max(10, i - 1500), i):
            d = _dist(q, feats[j])
            neighbors.append((d, labels[j]))
        neighbors.sort(key=lambda x: x[0])
        k = min(int(args.k), len(neighbors))
        vote = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
        for d, lab in neighbors[:k]:
            w = 1.0 / (1e-9 + d)
            vote[lab] += w
        pred = max(vote.keys(), key=lambda x: vote[x])
        rows.append({"eval_date": dates[i], "predicted_direction": pred})

    payload = {
        "schema": "btc_per_date_direction_knn_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "btc_csv": str(args.btc_csv if args.btc_csv.is_absolute() else (ROOT / args.btc_csv)),
            "horizon_days": int(args.horizon_days),
            "neutral_bps": float(args.neutral_bps),
            "k": int(args.k),
            "train_min": int(args.train_min),
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

