#!/usr/bin/env python3
"""[HYPO] Live fills execution-eval lane v1 — research_only; no Track A/live merge.

Summarizes cursor_trade_history fills cache for execution-aware validation (not OHLCV backtest).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FILLS_CACHE = ROOT / "reports/btrack_fills_daily_feature_cache_v1_latest.json"
TRADES_META = ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/trades_export_meta_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_fills_execution_eval_lane_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fills-cache", type=Path, default=FILLS_CACHE)
    ap.add_argument("--trades-meta", type=Path, default=TRADES_META)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.fills_cache.is_file():
        print(f"missing fills cache: {args.fills_cache}", file=sys.stderr)
        return 1

    cache = _load(args.fills_cache)
    meta = _load(args.trades_meta) if args.trades_meta.is_file() else {}

    daily = cache.get("daily_by_utc_date") if isinstance(cache.get("daily_by_utc_date"), dict) else {}
    dates = sorted(daily.keys())
    stats = cache.get("stats") if isinstance(cache.get("stats"), dict) else {}

    total_pnl = 0.0
    total_commission = 0.0
    total_quote = 0.0
    for row in daily.values():
        if isinstance(row, dict):
            total_pnl += float(row.get("realized_pnl_sum") or 0)
            total_commission += float(row.get("commission_sum") or 0)
            total_quote += float(row.get("quote_qty_sum") or 0)

    out: dict[str, Any] = {
        "schema": "btrack_fills_execution_eval_lane_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_active_write": False,
        "inputs": {
            "fills_cache": str(args.fills_cache.relative_to(ROOT)).replace("\\", "/"),
            "trades_meta": str(args.trades_meta.relative_to(ROOT)).replace("\\", "/")
            if args.trades_meta.is_file()
            else None,
        },
        "corpus": {
            "n_fill_rows": stats.get("n_fill_rows"),
            "n_daily_buckets": stats.get("n_daily_buckets"),
            "date_min": dates[0] if dates else None,
            "date_max": dates[-1] if dates else None,
            "export_hours": meta.get("hours"),
            "export_row_count": meta.get("row_count"),
            "symbol": meta.get("symbol") or "BTCUSDT",
        },
        "aggregates": {
            "realized_pnl_sum": round(total_pnl, 8),
            "commission_sum": round(total_commission, 8),
            "quote_qty_sum": round(total_quote, 4),
            "avg_fills_per_day": round(
                (stats.get("n_fill_rows") or 0) / max(len(dates), 1), 4
            ),
        },
        "vs_backtest_note_ko": (
            "OHLCV 장기 백테스트가 아닌 실체결(슬리피지·수수료·체결밀도) 코퍼스. "
            "n·기간·갭을 헤드라인에 반드시 병기."
        ),
        "gap_flags": {
            "sparse_vs_8760h_window": bool(meta.get("hours") == 8760.0 and (stats.get("n_fill_rows") or 0) < 3000),
            "recent_gap_after_date_max": dates[-1] if dates else None,
        },
        "lane_status": "ready_for_shadow_join",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out_json), "date_max": out["corpus"]["date_max"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
