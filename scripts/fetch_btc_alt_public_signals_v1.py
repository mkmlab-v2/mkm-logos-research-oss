#!/usr/bin/env python3
"""Fetch BTC alt public signals (no vendor code reuse).

Sources:
- CoinGecko public API (BTC market snapshot)
- Alternative.me Fear & Greed Index

Output:
- docs/final/artifacts/btc_alt_public_signals_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/btc_alt_public_signals_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _request_json(url: str, timeout: float = 15.0) -> Any:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _to_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _trend_label(score: float) -> str:
    if score > 0.15:
        return "up"
    if score < -0.15:
        return "down"
    return "flat"


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    try:
        cg = _request_json(
            "https://api.coingecko.com/api/v3/coins/bitcoin?"
            "localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        )
        fng = _request_json("https://api.alternative.me/fng/?limit=2")
    except (error.URLError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to fetch BTC alt public signals: {exc}", file=sys.stderr)
        return 1

    market = (cg or {}).get("market_data") if isinstance(cg, dict) else {}
    price_change_24h = _to_float((market or {}).get("price_change_percentage_24h"))
    market_cap_change_24h = _to_float((market or {}).get("market_cap_change_percentage_24h"))

    fng_now = None
    fng_prev = None
    rows = (fng or {}).get("data") if isinstance(fng, dict) else []
    if isinstance(rows, list):
        if len(rows) >= 1 and isinstance(rows[0], dict):
            fng_now = _to_float(rows[0].get("value"))
        if len(rows) >= 2 and isinstance(rows[1], dict):
            fng_prev = _to_float(rows[1].get("value"))

    score = 0.0
    if isinstance(price_change_24h, float):
        score += 0.6 if price_change_24h > 1.0 else (-0.6 if price_change_24h < -1.0 else 0.0)
    if isinstance(market_cap_change_24h, float):
        score += 0.4 if market_cap_change_24h > 1.0 else (-0.4 if market_cap_change_24h < -1.0 else 0.0)
    if isinstance(fng_now, float):
        score += -0.5 if fng_now > 75.0 else (0.5 if fng_now < 25.0 else 0.0)
    if isinstance(fng_now, float) and isinstance(fng_prev, float):
        d = fng_now - fng_prev
        score += -0.2 if d > 8.0 else (0.2 if d < -8.0 else 0.0)

    doc = {
        "schema": "btc_alt_public_signals_v1",
        "ts_utc": _utc_now(),
        "source": {"coingecko": True, "alternative_fng": True},
        "trading_scope": {
            "primary_asset": "BTCUSDT",
            "mode": "btc_only",
        },
        "metrics": {
            "price_change_pct_24h": price_change_24h,
            "market_cap_change_pct_24h": market_cap_change_24h,
            "fear_greed_now": fng_now,
            "fear_greed_prev": fng_prev,
        },
        "alt_public_trend": {"trend": _trend_label(score), "score": round(score, 6)},
        "boundary_ack": True,
        "hypothesis_tier": "B",
        "note": "BTC public signals inspired by external terminal-style data mix; research_only.",
    }

    if args.dry_run:
        print(json.dumps(doc["alt_public_trend"], ensure_ascii=False, indent=2))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
