#!/usr/bin/env python3
"""Fetch BTC market microstructure signals (public Binance endpoints).

Output:
- docs/final/artifacts/btc_market_signals_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/btc_market_signals_latest.json"


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
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    symbol = args.symbol.strip().upper()
    try:
        premium = _request_json(
            f"https://fapi.binance.com/fapi/v1/premiumIndex?{parse.urlencode({'symbol': symbol})}"
        )
        oi = _request_json(
            f"https://fapi.binance.com/fapi/v1/openInterest?{parse.urlencode({'symbol': symbol})}"
        )
        long_short = _request_json(
            "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?"
            + parse.urlencode({"symbol": symbol, "period": "5m", "limit": 2})
        )
    except (error.URLError, json.JSONDecodeError) as exc:
        print(f"ERROR: failed to fetch Binance market signals: {exc}", file=sys.stderr)
        return 1

    mark_price = _to_float((premium or {}).get("markPrice")) if isinstance(premium, dict) else None
    funding_rate = _to_float((premium or {}).get("lastFundingRate")) if isinstance(premium, dict) else None
    open_interest = _to_float((oi or {}).get("openInterest")) if isinstance(oi, dict) else None

    long_short_now = None
    long_short_prev = None
    if isinstance(long_short, list):
        if len(long_short) >= 1 and isinstance(long_short[-1], dict):
            long_short_now = _to_float(long_short[-1].get("longShortRatio"))
        if len(long_short) >= 2 and isinstance(long_short[-2], dict):
            long_short_prev = _to_float(long_short[-2].get("longShortRatio"))

    score = 0.0
    # Positive funding/LS ratio leans crowded-long (risk of mean reversion).
    if funding_rate is not None:
        score += -1.0 if funding_rate > 0.0005 else (1.0 if funding_rate < -0.0005 else 0.0)
    if long_short_now is not None:
        score += -0.7 if long_short_now > 1.4 else (0.7 if long_short_now < 0.8 else 0.0)
    if long_short_now is not None and long_short_prev is not None:
        d = long_short_now - long_short_prev
        score += -0.4 if d > 0.1 else (0.4 if d < -0.1 else 0.0)
    if open_interest is not None and mark_price is not None:
        # Normalized rough crowding proxy.
        oi_notional_b = (open_interest * mark_price) / 1_000_000_000.0
        score += -0.3 if oi_notional_b > 12.0 else (0.2 if oi_notional_b < 4.0 else 0.0)

    doc = {
        "schema": "btc_market_signals_v1",
        "ts_utc": _utc_now(),
        "symbol": symbol,
        "trading_scope": {
            "primary_asset": "BTCUSDT",
            "mode": "btc_only",
        },
        "metrics": {
            "mark_price": mark_price,
            "funding_rate": funding_rate,
            "open_interest": open_interest,
            "long_short_ratio_now": long_short_now,
            "long_short_ratio_prev": long_short_prev,
        },
        "market_micro_trend": {"trend": _trend_label(score), "score": round(score, 6)},
        "boundary_ack": True,
        "hypothesis_tier": "B",
        "note": "BTC-specific market microstructure helper; research_only.",
    }

    if args.dry_run:
        print(json.dumps(doc["market_micro_trend"], ensure_ascii=False, indent=2))
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
