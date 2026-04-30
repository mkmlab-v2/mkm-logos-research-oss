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
MD = ROOT / "research" / "market_data"

DEFAULT_SHORT = ART / "btc_per_date_direction_regime_switch_multifactor_b_latest.json"
DEFAULT_MID = ART / "btc_per_date_direction_crossasset_multifactor_wf_h2_nb8_latest.json"
DEFAULT_LONG = ART / "btc_per_date_direction_causal_rule_select_latest.json"
DEFAULT_BTC = MD / "btc_daily_external_yf.csv"
DEFAULT_VIX = MD / "vix_daily_external_yf.csv"
DEFAULT_OUT = ART / "btc_per_date_direction_horizon_regime_router_latest.json"


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


def _load_close(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out[str(r["Date"])[:10]] = float(r["Close"])
    return out


def _load_close_optional(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    return _load_close(path)


def _ret(series: dict[str, float], dates: list[str], i: int, lag: int) -> float:
    if i < lag:
        return 0.0
    c0 = series.get(dates[i - lag], 0.0)
    c1 = series.get(dates[i - 1], 0.0)
    if c0 == 0:
        return 0.0
    return (c1 - c0) / c0


def _absret(series: dict[str, float], dates: list[str], i: int) -> float:
    if i < 1:
        return 0.0
    c0 = series.get(dates[i - 1], 0.0)
    c1 = series.get(dates[i], 0.0)
    if c0 == 0:
        return 0.0
    return abs((c1 - c0) / c0)


def main() -> int:
    ap = argparse.ArgumentParser(description="Horizon/regime router over short/mid/long source predictions.")
    ap.add_argument("--short-source", type=Path, default=DEFAULT_SHORT)
    ap.add_argument("--mid-source", type=Path, default=DEFAULT_MID)
    ap.add_argument("--long-source", type=Path, default=DEFAULT_LONG)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--vix-csv", type=Path, default=DEFAULT_VIX)
    ap.add_argument("--shock-vix-threshold", type=float, default=0.03)
    ap.add_argument("--trend-threshold", type=float, default=0.05)
    ap.add_argument("--trend-lag-days", type=int, default=20)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    short_src = _load_pred(args.short_source if args.short_source.is_absolute() else ROOT / args.short_source)
    mid_src = _load_pred(args.mid_source if args.mid_source.is_absolute() else ROOT / args.mid_source)
    long_src = _load_pred(args.long_source if args.long_source.is_absolute() else ROOT / args.long_source)
    btc = _load_close(args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv)
    vix = _load_close_optional(args.vix_csv if args.vix_csv.is_absolute() else ROOT / args.vix_csv)

    dates = sorted(set(short_src.keys()) & set(mid_src.keys()) & set(long_src.keys()) & set(btc.keys()))

    rows: list[dict[str, Any]] = []
    route_count = {"short": 0, "mid": 0, "long": 0}
    for i, d in enumerate(dates):
        btc_trend = _ret(btc, dates, i, int(args.trend_lag_days))
        btc_shock = _absret(btc, dates, i)
        vix_ret = _ret(vix, dates, i, 1) if vix else 0.0

        # Regime routing:
        # - shock/high-vol days use short-horizon source
        # - strong trend days use long-horizon source
        # - otherwise mid source
        if btc_shock >= float(args.shock_vix_threshold) or abs(vix_ret) >= float(args.shock_vix_threshold):
            pred = short_src[d]
            route = "short"
        elif abs(btc_trend) >= float(args.trend_threshold):
            pred = long_src[d]
            route = "long"
        else:
            pred = mid_src[d]
            route = "mid"

        route_count[route] += 1
        rows.append({"eval_date": d, "predicted_direction": pred})

    payload = {
        "schema": "btc_per_date_direction_horizon_regime_router_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "short_source": str(args.short_source),
            "mid_source": str(args.mid_source),
            "long_source": str(args.long_source),
            "btc_csv": str(args.btc_csv),
            "vix_csv": str(args.vix_csv),
            "shock_vix_threshold": float(args.shock_vix_threshold),
            "trend_threshold": float(args.trend_threshold),
            "trend_lag_days": int(args.trend_lag_days),
        },
        "route_count": route_count,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)} routes={route_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

