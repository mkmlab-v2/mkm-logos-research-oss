#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_A = ART / "btc_per_date_direction_crossasset_multifactor_wf_h2_nb8_latest.json"
DEFAULT_B = ART / "btc_per_date_direction_regime_switch_multifactor_b_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ART / "btc_per_date_direction_adaptive_selector_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_pred(path: Path) -> dict[str, str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    out: dict[str, str] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        d = str(r.get("eval_date") or "")[:10]
        p = str(r.get("predicted_direction") or "").lower()
        if d and p in ("bull", "bear", "neutral"):
            out[d] = p
    return out


def _load_close(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append((str(r["Date"])[:10], float(r["Close"])))
    rows.sort(key=lambda x: x[0])
    return rows


def _label(closes: list[float], i: int, h: int, neutral_bps: float) -> str:
    j = i + h
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Adaptive selector between two BTC per-date prediction sources.")
    ap.add_argument("--source-a", type=Path, default=DEFAULT_A)
    ap.add_argument("--source-b", type=Path, default=DEFAULT_B)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--horizon-days", type=int, default=2)
    ap.add_argument("--neutral-bps", type=float, default=8.0)
    ap.add_argument("--train-min", type=int, default=320)
    ap.add_argument("--lookback", type=int, default=180)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src_a = _load_pred(args.source_a if args.source_a.is_absolute() else ROOT / args.source_a)
    src_b = _load_pred(args.source_b if args.source_b.is_absolute() else ROOT / args.source_b)
    px = _load_close(args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv)
    dates = [d for d, _ in px]
    closes = [c for _, c in px]
    idx = {d: i for i, d in enumerate(dates)}

    shared_dates = sorted(set(src_a.keys()) & set(src_b.keys()) & set(idx.keys()))
    labels: dict[str, str] = {}
    for d in shared_dates:
        i = idx[d]
        labels[d] = _label(closes, i, int(args.horizon_days), float(args.neutral_bps))

    rows: list[dict[str, Any]] = []
    for d in shared_dates:
        i = idx[d]
        if i < int(args.train_min):
            continue
        # trailing realized labels only (no future leakage)
        lo = max(0, i - int(args.lookback))
        hist_dates = [dates[k] for k in range(lo, i) if dates[k] in labels]
        if len(hist_dates) < 40:
            pred = src_a[d]
            rows.append({"eval_date": d, "predicted_direction": pred})
            continue

        hit_a = 0
        hit_b = 0
        n = 0
        for hd in hist_dates:
            act = labels[hd]
            pa = src_a.get(hd)
            pb = src_b.get(hd)
            if pa is None or pb is None:
                continue
            n += 1
            hit_a += 1 if pa == act else 0
            hit_b += 1 if pb == act else 0
        if n == 0:
            pred = src_a[d]
        else:
            pred = src_a[d] if hit_a >= hit_b else src_b[d]
        rows.append({"eval_date": d, "predicted_direction": pred})

    out = {
        "schema": "btc_per_date_direction_adaptive_selector_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "source_a": str(args.source_a),
            "source_b": str(args.source_b),
            "btc_csv": str(args.btc_csv),
            "horizon_days": int(args.horizon_days),
            "neutral_bps": float(args.neutral_bps),
            "train_min": int(args.train_min),
            "lookback": int(args.lookback),
            "policy": "choose_source_with_higher_trailing_hit_rate",
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

