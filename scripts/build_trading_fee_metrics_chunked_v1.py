#!/usr/bin/env python3
"""
Aggregate Binance USDT-M futures user trades over >7d by chunking (API max interval 7 days).

Writes:
  reports/trading_window_export_30d_v1/trades_treatment.json (deduped, normalized)
  reports/trading_window_metrics_chunked_30d_v1.json (sums + maker/taker counts)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BT = ROOT / "projects" / "bitcoin-trading"
if str(BT) not in sys.path:
    sys.path.insert(0, str(BT))

from src.api.binance_client import BinanceFuturesClient  # noqa: E402


def _row_from_native(r: dict[str, Any]) -> dict[str, Any]:
    t_ms = int(r.get("time") or 0)
    mk = r.get("maker")
    if mk is None and "isMaker" in r:
        mk = r.get("isMaker")
    return {
        "timestamp": t_ms,
        "time": t_ms,
        "symbol": r.get("symbol"),
        "side": str(r.get("side") or "").upper(),
        "position_side": str(r.get("positionSide") or "BOTH").upper(),
        "price": float(r.get("price") or 0),
        "amount": float(r.get("qty") or 0),
        "quote_qty": float(r.get("quoteQty") or 0),
        "realized_pnl": float(r.get("realizedPnl") or 0),
        "commission": float(r.get("commission") or 0),
        "order_id": r.get("orderId"),
        "trade_id": r.get("id"),
        "maker": mk,
        "status": "filled",
        "source": "binance_futures_account_trades",
    }


def _dedupe_key(r: dict[str, Any]) -> tuple[Any, Any]:
    return (r.get("symbol"), r.get("trade_id"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=30, help="Total lookback (default 30).")
    ap.add_argument(
        "--chunk-hours",
        type=int,
        default=144,
        help="Per-request window in hours (default 144 = 6d, under Binance 7d cap).",
    )
    ap.add_argument("--max-trades-per-chunk", type=int, default=15_000)
    ap.add_argument("--sleep-sec", type=float, default=0.25, help="Between API chunk calls.")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "reports" / "trading_window_export_30d_v1",
    )
    ap.add_argument(
        "--metrics-out",
        type=Path,
        default=ROOT / "reports" / "trading_window_metrics_chunked_30d_v1.json",
    )
    ap.add_argument("--testnet", action="store_true")
    args = ap.parse_args()

    chunk_ms = int(args.chunk_hours) * 3600 * 1000
    total_ms = int(args.days) * 24 * 3600 * 1000
    if chunk_ms > 7 * 24 * 3600 * 1000 - 60_000:
        print("chunk_hours must keep window under Binance 7d limit; got too large.", file=sys.stderr)
        return 2

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    end_ms = now_ms
    start_floor = end_ms - total_ms

    client = BinanceFuturesClient(testnet=bool(args.testnet))
    raw_by_id: dict[tuple[Any, Any], dict[str, Any]] = {}
    chunk_meta: list[dict[str, Any]] = []
    chunk_end = end_ms
    while chunk_end > start_floor:
        chunk_start = max(start_floor, chunk_end - chunk_ms)
        t0 = time.perf_counter()
        try:
            batch = client.fetch_futures_trades_time_range(
                args.symbol,
                start_ms=chunk_start,
                end_ms=chunk_end,
                max_trades=int(args.max_trades_per_chunk),
            )
        except Exception as e:
            chunk_meta.append(
                {
                    "chunk_start_ms": chunk_start,
                    "chunk_end_ms": chunk_end,
                    "ok": False,
                    "error": str(e)[:500],
                }
            )
            chunk_end = chunk_start
            time.sleep(args.sleep_sec)
            continue

        added = 0
        for row in batch:
            if not isinstance(row, dict):
                continue
            if "time" in row and "realizedPnl" in row:
                norm = _row_from_native(row)
            else:
                continue
            k = _dedupe_key(norm)
            if k[1] is None:
                continue
            raw_by_id[k] = norm
            added += 1

        chunk_meta.append(
            {
                "chunk_start_ms": chunk_start,
                "chunk_end_ms": chunk_end,
                "ok": True,
                "raw_rows": len(batch),
                "normalized_added": added,
                "elapsed_sec": round(time.perf_counter() - t0, 3),
            }
        )
        chunk_end = chunk_start
        time.sleep(args.sleep_sec)

    rows = sorted(raw_by_id.values(), key=lambda r: (int(r.get("timestamp") or 0), int(r.get("trade_id") or 0)))

    realized = sum(float(r.get("realized_pnl") or 0) for r in rows)
    comm = sum(float(r.get("commission") or 0) for r in rows)
    makers = [r for r in rows if r.get("maker") is True]
    takers = [r for r in rows if r.get("maker") is False]
    unknown = [r for r in rows if r.get("maker") not in (True, False)]
    n = len(rows)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "trades_treatment.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    meta = {
        "schema": "trades_export_meta_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": args.symbol,
        "days_requested": int(args.days),
        "chunk_hours": int(args.chunk_hours),
        "row_count_deduped": n,
        "testnet": bool(args.testnet),
        "chunks": chunk_meta,
    }
    (out_dir / "trades_export_meta_v1.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    metrics = {
        "schema": "trading_window_metrics_chunked_30d_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "window_note": f"Chunked fetch: {args.days}d lookback, {args.chunk_hours}h windows, deduped by (symbol, trade_id).",
        "source_dir": str(out_dir).replace("\\", "/"),
        "row_count": n,
        "sum_realized_pnl": round(realized, 8),
        "sum_commission": round(comm, 8),
        "sum_realized_minus_commission": round(realized - comm, 8),
        "maker_count": len(makers),
        "taker_count": len(takers),
        "unknown_maker_flag_count": len(unknown),
        "maker_share": round(len(makers) / n, 6) if n else None,
        "taker_share": round(len(takers) / n, 6) if n else None,
        "chunks": chunk_meta,
    }
    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[ok] rows={n} realized={realized:.4f} commission={comm:.4f} net={realized - comm:.4f}")
    print(f"     wrote {out_dir} and {args.metrics_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
