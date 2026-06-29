#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.8, K:0.52, M:0.3}
# Balance: 85
# Purpose: Aggregate cursor_trade_history fills into daily execution feature cache (B-track)
# Keywords: prophecy, fills, slippage, cache, cursor_trade_history
"""Aggregate Binance/cursor trade history rows into daily execution feature cache.

Contract: ``docs/final/schemas/btc_archive_feature_transformer_draft_v1.schema.json``
Output is research_only; does not auto-join align-panel without human+ablation.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRADES = ROOT / "projects" / "bitcoin-trading" / "exports" / "cursor_trade_history" / "trades_treatment.json"
DEFAULT_OUT = ROOT / "reports" / "btrack_fills_daily_feature_cache_v1_latest.json"
SCHEMA = "btrack_fills_daily_feature_cache_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_trade_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        for key in ("trades", "rows", "fills", "treatment"):
            val = raw.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _ts_to_date_ms(ts: Any) -> str | None:
    if ts is None:
        return None
    try:
        t = int(ts)
    except (TypeError, ValueError):
        return None
    if t > 1_000_000_000_000:
        t = t // 1000
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")


def aggregate_fills_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    """Map UTC calendar date -> execution feature row (draft contract)."""
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        d = _ts_to_date_ms(r.get("timestamp") or r.get("time"))
        if d:
            buckets[d].append(r)

    out: dict[str, dict[str, float | int]] = {}
    for d, items in sorted(buckets.items()):
        n = len(items)
        buy_n = sum(1 for x in items if str(x.get("side", "")).upper() in ("BUY", "LONG"))
        sell_n = sum(1 for x in items if str(x.get("side", "")).upper() in ("SELL", "SHORT"))
        maker_n = sum(1 for x in items if x.get("maker") is True)
        quote_sum = sum(float(x.get("quote_qty") or 0.0) for x in items)
        pnl_sum = sum(float(x.get("realized_pnl") or 0.0) for x in items)
        comm_sum = sum(float(x.get("commission") or 0.0) for x in items)
        prices = [float(x.get("price") or 0.0) for x in items if float(x.get("price") or 0.0) > 0]
        price_mean = (sum(prices) / len(prices)) if prices else 0.0
        price_std = 0.0
        if len(prices) > 1:
            mu = price_mean
            price_std = (sum((p - mu) ** 2 for p in prices) / len(prices)) ** 0.5
        out[d] = {
            "fill_count": n,
            "buy_fill_count": buy_n,
            "sell_fill_count": sell_n,
            "buy_sell_imbalance": (buy_n - sell_n) / n if n else 0.0,
            "maker_ratio": maker_n / n if n else 0.0,
            "quote_qty_sum": round(quote_sum, 8),
            "realized_pnl_sum": round(pnl_sum, 8),
            "commission_sum": round(comm_sum, 8),
            "price_mean": round(price_mean, 8),
            "price_dispersion": round(price_std, 8),
        }
    return out


def build_cache_document(*, trades_path: Path, generated_at_utc: str) -> dict[str, Any]:
    rows = _load_trade_rows(trades_path)
    daily = aggregate_fills_daily(rows)
    return {
        "schema": SCHEMA,
        "generated_at_utc": generated_at_utc,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "transformer_contract": "docs/final/schemas/btc_archive_feature_transformer_draft_v1.schema.json",
        "inputs": {
            "trades_json": str(trades_path),
            "source_schema": "cursor_trade_history_fill_row_v1",
        },
        "stats": {
            "n_fill_rows": len(rows),
            "n_daily_buckets": len(daily),
        },
        "daily_by_utc_date": daily,
        "align_panel_join_policy": {
            "auto_merge": False,
            "requires_human_signoff": True,
            "note": "Execution cache is additive B-track channel; expanded_prior remains OHLCV-derived.",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build daily execution feature cache from trade fills.")
    ap.add_argument("--trades-json", type=Path, default=DEFAULT_TRADES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_cache_document(trades_path=args.trades_json, generated_at_utc=_utc_now())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"ok fill_rows={doc['stats']['n_fill_rows']} "
        f"daily_buckets={doc['stats']['n_daily_buckets']} out={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
