#!/usr/bin/env python3
"""Evaluate war-prolongation directional significance with expanded samples.

Expands sample count by evaluating rolling event dates across each leg and horizon.
Observation lane only.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_SCORE = ART / "btrack_prophecy_score_war_prolong_20260406_multileg.json"
DEFAULT_OUT = ART / "war_prolongation_significance_eval_latest.json"
DEFAULT_MARKET_DIR = ROOT / "research" / "market_data"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _binom_sf(k: int, n: int, p: float) -> float:
    # P[X >= k] for X~Bin(n,p), computed in log-space for numeric stability.
    if n <= 0:
        return 1.0
    if p <= 0.0:
        return 1.0 if k <= 0 else 0.0
    if p >= 1.0:
        return 1.0 if k <= n else 0.0
    s = 0.0
    for i in range(k, n + 1):
        log_coeff = math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
        log_term = log_coeff + (i * math.log(p)) + ((n - i) * math.log(1 - p))
        s += math.exp(log_term)
    return min(1.0, max(0.0, s))


def _series(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    s = pd.Series(df["Close"].values, index=pd.to_datetime(df["Date"]).dt.date)
    return s.sort_index()


def main() -> int:
    ap = argparse.ArgumentParser(description="Expanded sample significance eval for war-prolongation hypothesis.")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--market-data-dir", type=Path, default=DEFAULT_MARKET_DIR)
    ap.add_argument("--lookback-days", type=int, default=120)
    ap.add_argument("--horizons", type=str, default="1,5,20")
    ap.add_argument("--baseline-hit-rate", type=float, default=1.0 / 3.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score = json.loads(args.score_json.read_text(encoding="utf-8"))
    rows = score.get("rows", [])
    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]

    samples: list[dict] = []
    warnings: list[str] = []
    for r in rows:
        leg = str(r.get("instrument") or "")
        symbol = str(r.get("symbol") or "")
        pred = str(r.get("predicted_direction") or "").lower()
        neutral_bps = float(r.get("neutral_bps") or 5.0)
        if pred not in ("bull", "bear", "neutral"):
            continue
        csv_path = args.market_data_dir / f"{leg}_daily_external_yf.csv"
        if not csv_path.is_file():
            warnings.append(f"missing_csv:{leg}")
            continue
        s = _series(csv_path)
        if len(s) < max(horizons) + 2:
            warnings.append(f"short_series:{leg}")
            continue

        start_idx = max(0, len(s) - args.lookback_days - max(horizons))
        end_idx = len(s) - max(horizons)
        for i in range(start_idx, end_idx):
            for h in horizons:
                c0 = float(s.iloc[i])
                c1 = float(s.iloc[i + h])
                if c0 == 0:
                    continue
                ret = (c1 - c0) / c0
                actual = _actual_direction(ret, neutral_bps)
                hit = int(actual == pred)
                samples.append(
                    {
                        "instrument": leg,
                        "symbol": symbol,
                        "event_date": str(s.index[i]),
                        "horizon_days": h,
                        "predicted_direction": pred,
                        "actual_direction": actual,
                        "window_return": round(ret, 8),
                        "hit": hit,
                    }
                )

    n = len(samples)
    hits = sum(x["hit"] for x in samples)
    hit_rate = (hits / n) if n > 0 else None
    p_value = _binom_sf(hits, n, args.baseline_hit_rate) if n > 0 else None
    significant = bool(p_value is not None and p_value < 0.05)

    by_h = {}
    for h in horizons:
        sub = [x for x in samples if x["horizon_days"] == h]
        nh = len(sub)
        hh = sum(x["hit"] for x in sub)
        hr = (hh / nh) if nh > 0 else None
        pv = _binom_sf(hh, nh, args.baseline_hit_rate) if nh > 0 else None
        by_h[f"h{h}"] = {
            "n": nh,
            "hits": hh,
            "hit_rate": round(hr, 6) if hr is not None else None,
            "p_value_one_sided_vs_baseline": round(pv, 8) if pv is not None else None,
            "significant": bool(pv is not None and pv < 0.05),
        }

    out = {
        "schema": "war_prolongation_significance_eval_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "score_json": str(args.score_json).replace("\\", "/"),
            "market_data_dir": str(args.market_data_dir).replace("\\", "/"),
            "lookback_days": args.lookback_days,
            "horizons": horizons,
            "baseline_hit_rate": args.baseline_hit_rate,
        },
        "overall": {
            "n": n,
            "hits": hits,
            "hit_rate": round(hit_rate, 6) if hit_rate is not None else None,
            "p_value_one_sided_vs_baseline": round(p_value, 8) if p_value is not None else None,
            "significant": significant,
        },
        "by_horizon": by_h,
        "warnings": warnings,
        "notes": ["Observation lane only. Not for live trading promotion."],
    }
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

