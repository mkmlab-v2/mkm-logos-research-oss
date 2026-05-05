#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.85, L:0.75, K:0.5, M:0.65}
# Balance: 88
# Purpose: Pull Binance USDT-M futures fills into cursor_trade_history JSON inputs, then 24h sync can run.
# Keywords: binance, fills, cursor_trade_history, exports, SSOT

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.api.binance_client import USE_CCXT  # noqa: E402
from src.api.binance_client import BinanceFuturesClient  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Export Binance futures account trades into trades_treatment.json (+ empty control) "
        "for sync_cursor_trade_history_latest_24h.py."
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=_PROJECT_ROOT / "exports" / "cursor_trade_history",
        help="Directory for trades_control.json and trades_treatment.json",
    )
    p.add_argument("--symbol", default="BTCUSDT", help="Futures symbol, e.g. BTCUSDT")
    p.add_argument(
        "--hours",
        type=float,
        default=168.0,
        help="How far back to fetch (default 168h = 7d). Sync still emits a 24h window file.",
    )
    p.add_argument("--max-trades", type=int, default=20_000, help="Hard cap on rows fetched")
    p.add_argument(
        "--testnet",
        action="store_true",
        help="Use BinanceFuturesClient(testnet=True). Default: mainnet if flag omitted.",
    )
    p.add_argument(
        "--run-sync",
        action="store_true",
        help="After export, run sync_cursor_trade_history_latest_24h.py on the same directory.",
    )
    p.add_argument(
        "--sync-hours",
        type=int,
        default=24,
        help="--hours passed to sync script when --run-sync is set.",
    )
    p.add_argument(
        "--run-promotion-gate",
        action="store_true",
        help="Forward --run-promotion-gate to sync when --run-sync is set.",
    )
    return p.parse_args()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _row_from_native(r: dict[str, Any]) -> dict[str, Any]:
    t_ms = int(r.get("time") or 0)
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
        "maker": r.get("maker"),
        "status": "filled",
        "source": "binance_futures_account_trades",
    }


def _row_from_ccxt(t: dict[str, Any]) -> dict[str, Any]:
    info = t.get("info") or {}
    ts = int(t.get("timestamp") or 0)
    side = str(t.get("side") or "").lower()
    if side == "buy":
        side_u = "BUY"
    elif side == "sell":
        side_u = "SELL"
    else:
        side_u = str(t.get("side") or "").upper()
    price = float(t.get("price") or info.get("price") or 0)
    amount = float(t.get("amount") or 0)
    rpnl_f = float(info.get("realizedPnl") or 0)
    comm = float(info.get("commission") or 0)
    if not comm and isinstance(t.get("fee"), dict):
        comm = float(t.get("fee", {}).get("cost") or 0)
    sym = info.get("symbol") or str(t.get("symbol") or "")
    qqty = float(info.get("quoteQty") or (price * amount))
    return {
        "timestamp": ts,
        "time": ts,
        "symbol": sym,
        "side": side_u,
        "position_side": str(info.get("positionSide") or "BOTH").upper(),
        "price": price,
        "amount": amount,
        "quote_qty": qqty,
        "realized_pnl": rpnl_f,
        "commission": comm,
        "order_id": info.get("orderId"),
        "trade_id": info.get("id") or t.get("id"),
        "maker": info.get("maker"),
        "status": "filled",
        "source": "ccxt_futures_user_trades",
    }


def _normalize_rows(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        if "realizedPnl" in row and "time" in row:
            out.append(_row_from_native(row))
        else:
            out.append(_row_from_ccxt(row))
    # Stable sort by time then trade id
    def _key(r: dict[str, Any]) -> tuple:
        return (int(r.get("timestamp") or 0), int(r.get("trade_id") or 0))

    out.sort(key=_key)
    return out


def main() -> int:
    args = _parse_args()
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=float(args.hours))
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    client = BinanceFuturesClient(testnet=bool(args.testnet))
    raw = client.fetch_futures_trades_time_range(
        args.symbol,
        start_ms=start_ms,
        end_ms=end_ms,
        max_trades=int(args.max_trades),
    )
    treatment = _normalize_rows([x for x in raw if isinstance(x, dict)])

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_json(out_dir / "trades_control.json", [])
    _write_json(out_dir / "trades_treatment.json", treatment)
    _write_json(
        out_dir / "trades_export_meta_v1.json",
        {
            "schema": "trades_export_meta_v1",
            "generated_at_utc": now.isoformat(),
            "symbol": args.symbol,
            "hours": float(args.hours),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "row_count": len(treatment),
            "use_ccxt": bool(USE_CCXT),
            "testnet": bool(args.testnet),
        },
    )

    print(f"[OK] wrote trades_treatment.json rows={len(treatment)} -> {out_dir}")
    print(f"     window_utc: {start.isoformat()} .. {now.isoformat()}")

    if args.run_sync:
        sync_script = Path(__file__).resolve().parent / "sync_cursor_trade_history_latest_24h.py"
        cmd = [
            sys.executable,
            str(sync_script),
            "--source-dir",
            str(out_dir),
            "--dest-dir",
            str(out_dir),
            "--hours",
            str(int(args.sync_hours)),
        ]
        if args.run_promotion_gate:
            cmd.append("--run-promotion-gate")
        print("[INFO] running:", " ".join(cmd))
        r = subprocess.run(cmd, check=False)
        return int(r.returncode)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
