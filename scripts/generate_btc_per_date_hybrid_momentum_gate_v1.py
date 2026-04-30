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
DEFAULT_SRC = ART / "btc_per_date_direction_crossasset_multifactor_wf_h2_nb8_latest.json"
DEFAULT_BTC = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ART / "btc_per_date_direction_hybrid_momentum_gate_latest.json"


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


def _load_prices(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append((str(r["Date"])[:10], float(r["Close"])))
    rows.sort(key=lambda x: x[0])
    return rows


def _ret(closes: list[float], i: int, lag: int) -> float:
    if i < lag:
        return 0.0
    c0 = closes[i - lag]
    c1 = closes[i - 1]
    if c0 == 0:
        return 0.0
    return (c1 - c0) / c0


def _vol(closes: list[float], i: int, k: int) -> float:
    if i < k:
        return 0.0
    vals: list[float] = []
    for j in range(i - k + 1, i + 1):
        c0 = closes[j - 1]
        c1 = closes[j]
        if c0 != 0:
            vals.append(abs((c1 - c0) / c0))
    return float(sum(vals) / len(vals)) if vals else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid source: base predictions gated by BTC momentum/volatility regime.")
    ap.add_argument("--source-json", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--mom-lag", type=int, default=5)
    ap.add_argument("--mom-threshold", type=float, default=0.012)
    ap.add_argument("--high-vol-threshold", type=float, default=0.022)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src = _load_pred(args.source_json if args.source_json.is_absolute() else (ROOT / args.source_json))
    px = _load_prices(args.btc_csv if args.btc_csv.is_absolute() else (ROOT / args.btc_csv))
    dates = [d for d, _ in px]
    closes = [c for _, c in px]
    idx = {d: i for i, d in enumerate(dates)}

    rows: list[dict[str, Any]] = []
    for d, base in sorted(src.items()):
        i = idx.get(d)
        if i is None:
            continue
        mom = _ret(closes, i, int(args.mom_lag))
        v10 = _vol(closes, i, 10)
        pred = base

        # Rule 1: strong momentum -> follow trend (bull/bear), unless volatility is very high.
        if abs(mom) >= float(args.mom_threshold) and v10 < float(args.high_vol_threshold):
            pred = "bull" if mom > 0 else "bear"
        # Rule 2: high vol + weak momentum -> neutralize to reduce noisy flips.
        elif v10 >= float(args.high_vol_threshold) and abs(mom) < float(args.mom_threshold):
            pred = "neutral"

        rows.append({"eval_date": d, "predicted_direction": pred})

    out = {
        "schema": "btc_per_date_direction_hybrid_momentum_gate_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "source_json": str(args.source_json),
            "btc_csv": str(args.btc_csv),
            "mom_lag": int(args.mom_lag),
            "mom_threshold": float(args.mom_threshold),
            "high_vol_threshold": float(args.high_vol_threshold),
            "policy": "follow_strong_momentum_else_neutralize_high_vol",
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

