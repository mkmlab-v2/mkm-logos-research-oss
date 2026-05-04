#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-shot USDⓈ-M futures market order via BinanceFuturesClient (Security Agent / env keys).

Default-safe: no order is sent unless ``--live`` is passed. Defaults to testnet unless ``--mainnet``.

Does not start PM2 or long-running daemons.

Usage (dry-run / intent only):
  py projects/bitcoin-trading/scripts/execute_binance_usdm_single_order_v1.py \\
    --symbol BTCUSDT --side BUY --qty 0.001

Live testnet:
  py ... --symbol BTCUSDT --side BUY --qty 0.001 --live

Live mainnet (careful):
  py ... --symbol BTCUSDT --side BUY --qty 0.001 --live --mainnet
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _BT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

DEFAULT_SUMMARY = Path("reports/binance_usdm_single_order/run_summary_latest.json")


def _workspace_root() -> Path:
    """Monorepo root (…/workspace): scripts live under projects/bitcoin-trading/scripts/."""
    return Path(__file__).resolve().parents[3]


def _append_strike_audit(summary: dict[str, Any], summary_path: Path) -> None:
    """Append-only: pilot journal + agent_decisions_log (live strikes only; Fact-Lock trail)."""
    if not summary.get("live"):
        return
    ts = str(summary.get("ts_utc") or datetime.now(timezone.utc).isoformat())
    order = summary.get("order") if isinstance(summary.get("order"), dict) else {}
    oid = order.get("orderId")
    summary_path = summary_path.resolve()
    journal_path = summary_path.parent / "pilot_order_journal.jsonl"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_row = {
        "schema": "binance_usdm_pilot_journal_v1",
        "ts_utc": ts,
        "rail": "strike_pilot_usdm_v1",
        "live": summary.get("live"),
        "testnet": summary.get("testnet"),
        "symbol": summary.get("symbol"),
        "side": summary.get("side"),
        "qty": summary.get("qty"),
        "leverage": summary.get("leverage"),
        "ok": summary.get("ok"),
        "order_id": oid,
        "order_status": order.get("status"),
        "executed_qty": order.get("executedQty"),
        "order_type": order.get("type"),
        "summary_path": str(summary_path).replace("\\", "/"),
    }
    with journal_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(journal_row, ensure_ascii=False) + "\n")

    agent_path = _workspace_root() / "reports" / "agent_decisions_log.jsonl"
    agent_path.parent.mkdir(parents=True, exist_ok=True)
    risk = "medium" if summary.get("testnet") else "high"
    decision = "order_submitted" if summary.get("ok") else "order_failed"
    note = (
        f"{summary.get('symbol')} {summary.get('side')} qty={summary.get('qty')} "
        f"mainnet={not summary.get('testnet', True)} orderId={oid} err={summary.get('error')}"
    )
    agent_row = {
        "timestamp": ts,
        "mission_id": "binance-usdm-pilot-strike",
        "stage": "execute",
        "decision": decision,
        "evidence_path": str(summary_path).replace("\\", "/"),
        "actor": "execute_binance_usdm_single_order_v1",
        "risk_level": risk,
        "retry_count": 0,
        "note": note[:500],
    }
    with agent_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(agent_row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Single USD-M futures market order (one-shot).")
    p.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    p.add_argument("--side", required=True, choices=("BUY", "SELL"), help="BUY=long entry, SELL=short entry (hedge mode)")
    p.add_argument(
        "--qty",
        type=float,
        required=True,
        help="Order quantity (contracts). Must match symbol LOT_SIZE step (e.g. BTCUSDT often step 0.001 — use 0.001 not 0.0005).",
    )
    p.add_argument("--leverage", type=int, default=2, help="Leverage (set before order)")
    p.add_argument(
        "--mainnet",
        action="store_true",
        help="Use mainnet (default is testnet). Pair with --live only after verification.",
    )
    p.add_argument(
        "--live",
        action="store_true",
        help="Actually submit the order. Without this flag, only writes intent summary (dry-run).",
    )
    p.add_argument("--out", type=Path, default=DEFAULT_SUMMARY, help="JSON summary path")
    args = p.parse_args(argv)

    testnet = not args.mainnet
    summary: dict[str, Any] = {
        "schema": "binance_usdm_single_order_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": args.symbol,
        "side": args.side,
        "qty": args.qty,
        "leverage": args.leverage,
        "testnet": testnet,
        "live": bool(args.live),
        "ok": False,
        "order": None,
        "error": None,
    }

    if args.qty <= 0:
        summary["error"] = "invalid_qty"
        _write_summary(args.out, summary)
        _append_strike_audit(summary, args.out)
        print("qty must be positive", file=sys.stderr)
        return 2

    if not args.live:
        summary["ok"] = True
        summary["note"] = "dry_run_no_http_order"
        _write_summary(args.out, summary)
        print(f"[dry-run] would place {args.side} {args.qty} {args.symbol} testnet={testnet}")
        return 0

    try:
        from api.binance_client import BinanceFuturesClient
    except ImportError as e:
        summary["error"] = f"import:{e}"
        _write_summary(args.out, summary)
        _append_strike_audit(summary, args.out)
        print(f"Import error: {e}", file=sys.stderr)
        return 2

    try:
        client = BinanceFuturesClient(testnet=testnet, maker_only=False)
    except Exception as e:
        summary["error"] = str(e)
        _write_summary(args.out, summary)
        _append_strike_audit(summary, args.out)
        print(f"Client init failed: {e}", file=sys.stderr)
        return 2

    try:
        if args.side == "BUY":
            order = client.open_long_position(symbol=args.symbol, quantity=args.qty, leverage=args.leverage)
        else:
            order = client.open_short_position(symbol=args.symbol, quantity=args.qty, leverage=args.leverage)
        summary["ok"] = order is not None
        summary["order"] = order
        if order is None:
            summary["error"] = "order_returned_none"
    except Exception as e:
        summary["error"] = str(e)
        summary["ok"] = False

    _write_summary(args.out, summary)
    _append_strike_audit(summary, args.out)
    if summary.get("ok"):
        print(f"[ok] order submitted summary={args.out}")
        return 0
    print(f"[fail] {summary.get('error')} summary={args.out}", file=sys.stderr)
    return 1


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
