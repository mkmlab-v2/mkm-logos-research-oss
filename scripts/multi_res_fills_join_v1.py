#!/usr/bin/env python3
"""Build multi-resolution fills index (low-res daily + high-res row pointers).

  py scripts/multi_res_fills_join_v1.py
  py scripts/multi_res_fills_join_v1.py --trades-json tests/fixtures/multi_res_trades_smoke_v1.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRADES = ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment.json"
DEFAULT_OUT = ROOT / "reports/multi_res_fills_index_v1_latest.json"
CONTRACT = ROOT / "docs/final/artifacts/multi_res_trades_treatment_contract_v1_latest.json"
FALLBACKS = (
    ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment_v2_shadow.json",
    ROOT / "reports/vps_trades_treatment_24h_latest.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_trade_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        for key in ("trades", "rows", "fills", "treatment"):
            val = raw.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _ts_to_utc_date(ts: Any) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        s = ts.strip()
        if re.match(r"^\d+$", s):
            ts = int(s)
        else:
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
            except ValueError:
                return None
    try:
        t = int(ts)
    except (TypeError, ValueError):
        return None
    if t > 1_000_000_000_000:
        t = t // 1000
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")


def aggregate_fills_daily(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        d = _ts_to_utc_date(r.get("timestamp") or r.get("time"))
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


def resolve_trades_source(primary: Path) -> tuple[Path, list[dict[str, Any]], bool, str | None]:
    rows = _load_trade_rows(primary)
    if rows:
        return primary, rows, False, None
    for fb in FALLBACKS:
        fb_rows = _load_trade_rows(fb)
        if fb_rows:
            return fb, fb_rows, True, str(fb.relative_to(ROOT)).replace("\\", "/")
    return primary, [], False, None


def build_multi_res_index(
    *,
    trades_path: Path,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    source_path, rows, fallback_used, fallback_source = resolve_trades_source(trades_path)
    rel_source = str(source_path.relative_to(ROOT)).replace("\\", "/")
    daily = aggregate_fills_daily(rows)

    row_summaries: list[dict[str, Any]] = []
    coord_ids: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        utc_date = _ts_to_utc_date(r.get("timestamp") or r.get("time")) or "unknown"
        row_summaries.append(
            {
                "row_id": i,
                "utc_date": utc_date,
                "json_pointer": f"/{i}",
                "symbol": r.get("symbol"),
                "side": r.get("side"),
            }
        )
        if utc_date != "unknown":
            coord_ids[utc_date].append(i)

    coordinate_map = [
        {
            "coord": f"daily:{d}",
            "utc_date": d,
            "low_res_key": d,
            "high_res_row_ids": ids,
        }
        for d, ids in sorted(coord_ids.items())
    ]

    return {
        "schema": "multi_res_index_v1",
        "generated_at_utc": generated_at_utc or _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] multi-res fills index — not Track A quality claim",
        "meta": {
            "n_fill_rows": len(rows),
            "n_daily_buckets": len(daily),
            "trades_source": rel_source,
            "fallback_used": fallback_used,
            **({"fallback_source": fallback_source} if fallback_source else {}),
        },
        "low_res": {"daily_by_utc_date": daily},
        "high_res": {
            "row_pointer_base": rel_source,
            "row_summaries": row_summaries,
        },
        "coordinate_map": coordinate_map,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trades-json", type=Path, default=DEFAULT_TRADES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_multi_res_index(trades_path=args.trades_json.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"OK: n_fill_rows={doc['meta']['n_fill_rows']} "
        f"n_daily={doc['meta']['n_daily_buckets']} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
