#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_per_date_direction_regime_ensemble_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_rows(path: Path) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out.append((str(r["Date"])[:10], float(r["Close"])))
    out.sort(key=lambda x: x[0])
    return out


def _label(closes: list[float], i: int, horizon: int, neutral_bps: float) -> str:
    j = i + horizon
    if j >= len(closes):
        return "neutral"
    c0 = closes[i]
    c1 = closes[j]
    if c0 == 0:
        return "neutral"
    ret = (c1 - c0) / c0
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _regime(closes: list[float], i: int) -> str:
    # Uses only past information up to i (inclusive).
    if i < 12:
        return "mid_flat"
    c1 = closes[i]
    c4 = closes[i - 3]
    c11 = closes[i - 10]
    r3 = (c1 - c4) / c4 if c4 else 0.0
    r10 = (c1 - c11) / c11 if c11 else 0.0
    vals: list[float] = []
    for j in range(i - 9, i + 1):
        p0 = closes[j - 1]
        p1 = closes[j]
        if p0:
            vals.append(abs((p1 - p0) / p0))
    vol = (sum(vals) / len(vals)) if vals else 0.0
    vol_tag = "high" if vol >= 0.03 else ("low" if vol <= 0.015 else "mid")
    trend = r10 + 0.5 * r3
    trend_tag = "up" if trend > 0 else ("down" if trend < 0 else "flat")
    return f"{vol_tag}_{trend_tag}"


def _pred_knn(closes: list[float], labels: list[str], i: int, k: int) -> str:
    if i < 40:
        return "bull"
    # tiny feature vector
    def feat(t: int) -> tuple[float, float, float]:
        c = closes[t]
        a = closes[t - 1]
        b = closes[t - 3]
        d = closes[t - 10]
        r1 = (c - a) / a if a else 0.0
        r3 = (a - b) / b if b else 0.0
        r10 = (a - d) / d if d else 0.0
        return (r1, r3, r10)

    q = feat(i)
    dists: list[tuple[float, str]] = []
    for j in range(20, i):
        f = feat(j)
        d = ((q[0] - f[0]) ** 2 + (q[1] - f[1]) ** 2 + (q[2] - f[2]) ** 2) ** 0.5
        dists.append((d, labels[j]))
    dists.sort(key=lambda x: x[0])
    kk = min(k, len(dists))
    vote = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
    for d, lab in dists[:kk]:
        vote[lab] += 1.0 / (1e-9 + d)
    return max(vote, key=vote.get)


def _pred_momentum(closes: list[float], i: int) -> str:
    if i < 12:
        return "bull"
    c1 = closes[i - 1]
    c4 = closes[i - 3]
    c11 = closes[i - 10]
    r3 = (c1 - c4) / c4 if c4 else 0.0
    r10 = (c1 - c11) / c11 if c11 else 0.0
    s = 0.7 * r10 + 0.3 * r3
    if s > 0.003:
        return "bull"
    if s < -0.003:
        return "bear"
    return "neutral"


def _pred_meanrev(closes: list[float], i: int) -> str:
    if i < 5:
        return "neutral"
    c1 = closes[i - 1]
    c2 = closes[i - 2]
    c5 = closes[i - 5]
    r1 = (c1 - c2) / c2 if c2 else 0.0
    r5 = (c1 - c5) / c5 if c5 else 0.0
    if r1 > 0.01 and r5 > 0.02:
        return "bear"
    if r1 < -0.01 and r5 < -0.02:
        return "bull"
    return "neutral"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate BTC per-date direction by regime-conditioned ensemble.")
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--horizon-days", type=int, default=2)
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--train-min", type=int, default=320)
    ap.add_argument("--knn-k", type=int, default=35)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _load_rows(args.btc_csv if args.btc_csv.is_absolute() else (ROOT / args.btc_csv))
    dates = [d for d, _ in rows]
    closes = [c for _, c in rows]
    labels = [_label(closes, i, int(args.horizon_days), float(args.neutral_bps)) for i in range(len(closes))]

    rows_out: list[dict[str, str]] = []
    for i in range(max(int(args.train_min), 30), len(dates) - int(args.horizon_days)):
        rg = _regime(closes, i)
        # Lightweight regime-conditioned static blend.
        if rg.startswith("high_"):
            best_w = (0.5, 0.8, 1.2)  # mean-reversion heavier in high-vol regimes
        elif rg.endswith("_up"):
            best_w = (1.2, 1.0, 0.4)  # follow momentum + knn in up-trend
        elif rg.endswith("_down"):
            best_w = (1.0, 1.2, 0.6)
        else:
            best_w = (1.1, 0.9, 0.7)

        p1 = _pred_knn(closes, labels, i, int(args.knn_k))
        p2 = _pred_momentum(closes, i)
        p3 = _pred_meanrev(closes, i)
        vote = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
        vote[p1] += best_w[0]
        vote[p2] += best_w[1]
        vote[p3] += best_w[2]
        pred = max(vote, key=vote.get)
        rows_out.append({"eval_date": dates[i], "predicted_direction": pred})

    payload = {
        "schema": "btc_per_date_direction_regime_ensemble_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "horizon_days": int(args.horizon_days),
            "neutral_bps": float(args.neutral_bps),
            "train_min": int(args.train_min),
            "knn_k": int(args.knn_k),
        },
        "rows": rows_out,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

