#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Place reduce-only STOP_MARKET (SL) and/or TAKE_PROFIT_MARKET (TP) on an open USD-M hedge position.

Default: dry-run (writes intent JSON only). Live orders require ``--live``.
Requires existing position on symbol (from ``get_position``).

Price inputs (one mode):
  - Absolute: ``--stop-loss-price`` / ``--take-profit-price`` (each optional; at least one required).
  - Offsets from entry: ``--sl-offset-pct`` / ``--tp-offset-pct`` (percent, e.g. 0.5 = 0.5%).

python-binance path only for live placement (CCXT not implemented for conditional orders).

Usage:
  py projects/bitcoin-trading/scripts/execute_binance_usdm_protective_orders_v1.py \\
    --symbol BTCUSDT --tp-offset-pct 0.8 --sl-offset-pct 0.4 --mainnet

  py ... --take-profit-price 99000 --stop-loss-price 92000 --live --mainnet
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_BT_ROOT = Path(__file__).resolve().parents[1]
_SRC = _BT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

DEFAULT_OUT = Path("reports/binance_usdm_single_order/protective_orders_latest.json")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _append_protective_audit(summary: dict[str, Any], summary_path: Path) -> None:
    if not summary.get("live"):
        return
    ts = str(summary.get("ts_utc") or datetime.now(timezone.utc).isoformat())
    summary_path = summary_path.resolve()
    journal_path = summary_path.parent / "pilot_order_journal.jsonl"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    sl_o = summary.get("stop_loss") or {}
    tp_o = summary.get("take_profit") or {}
    if not isinstance(sl_o, dict):
        sl_o = {}
    if not isinstance(tp_o, dict):
        tp_o = {}
    sl_ord = sl_o.get("order") if isinstance(sl_o.get("order"), dict) else {}
    tp_ord = tp_o.get("order") if isinstance(tp_o.get("order"), dict) else {}
    row = {
        "schema": "binance_usdm_pilot_journal_v1",
        "ts_utc": ts,
        "rail": "strike_protective_usdm_v1",
        "live": summary.get("live"),
        "testnet": summary.get("testnet"),
        "symbol": summary.get("symbol"),
        "ok": summary.get("ok"),
        "stop_loss_order_id": sl_ord.get("orderId"),
        "take_profit_order_id": tp_ord.get("orderId"),
        "summary_path": str(summary_path).replace("\\", "/"),
    }
    with journal_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    agent_path = _workspace_root() / "reports" / "agent_decisions_log.jsonl"
    agent_path.parent.mkdir(parents=True, exist_ok=True)
    risk = "medium" if summary.get("testnet") else "high"
    note = (
        f"protective {summary.get('symbol')} sl_id={row['stop_loss_order_id']} "
        f"tp_id={row['take_profit_order_id']} err={summary.get('error')}"
    )[:500]
    agent_row = {
        "timestamp": ts,
        "mission_id": "binance-usdm-protective-orders",
        "stage": "execute",
        "decision": "protective_orders_submitted" if summary.get("ok") else "protective_orders_failed",
        "evidence_path": str(summary_path).replace("\\", "/"),
        "actor": "execute_binance_usdm_protective_orders_v1",
        "risk_level": risk,
        "retry_count": 0,
        "note": note,
    }
    with agent_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(agent_row, ensure_ascii=False) + "\n")


def _run_execution_gate_or_fail(summary: dict[str, Any], out_path: Path) -> tuple[bool, str]:
    workspace = _workspace_root()
    gate_script = workspace / "scripts" / "run_execution_gate_v1.py"
    if not gate_script.exists():
        return False, f"execution_gate_script_missing:{gate_script.as_posix()}"

    intent_path = out_path.parent / "protective_order_intent_latest.json"
    intent_payload = {
        "schema": "execution_intent_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "request_id": f"protective-{summary.get('symbol', 'unknown')}",
        "symbol": summary.get("symbol"),
        "side": "REDUCE_ONLY_PROTECTIVE",
        "qty": (summary.get("planned") or {}).get("quantity"),
        "intent_type": "protective_orders",
        "testnet": summary.get("testnet"),
    }
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        json.dumps(intent_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    decision_path = out_path.parent / "execution_gate_decision_latest.json"
    cmd = [
        sys.executable,
        str(gate_script),
        "--intent-path",
        str(intent_path),
        "--output-path",
        str(decision_path),
    ]
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True)
    if proc.returncode == 0:
        return True, ""

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    reason = stderr or stdout or f"execution_gate_blocked_exit:{proc.returncode}"
    return False, reason


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="USD-M reduce-only TP/SL (STOP / TAKE_PROFIT MARKET).")
    p.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    p.add_argument("--mainnet", action="store_true", help="Mainnet (default testnet).")
    p.add_argument("--live", action="store_true", help="Submit orders (default dry-run).")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="JSON summary path.")
    p.add_argument("--working-type", default="MARK_PRICE", choices=("MARK_PRICE", "CONTRACT_PRICE"))
    p.add_argument("--stop-loss-price", type=float, default=None)
    p.add_argument("--take-profit-price", type=float, default=None)
    p.add_argument("--sl-offset-pct", type=float, default=None, help="Stop distance from entry in %% (e.g. 0.5).")
    p.add_argument("--tp-offset-pct", type=float, default=None, help="TP distance from entry in %% (e.g. 1.0).")
    args = p.parse_args(argv)

    testnet = not args.mainnet
    summary: dict[str, Any] = {
        "schema": "binance_usdm_protective_orders_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": args.symbol,
        "testnet": testnet,
        "live": bool(args.live),
        "working_type": args.working_type,
        "ok": False,
        "position": None,
        "stop_loss": None,
        "take_profit": None,
        "error": None,
    }

    has_abs = args.stop_loss_price is not None or args.take_profit_price is not None
    has_pct = args.sl_offset_pct is not None or args.tp_offset_pct is not None
    if has_abs and has_pct:
        summary["error"] = "use_either_absolute_or_pct_not_both"
        _write_summary(args.out, summary)
        print(summary["error"], file=sys.stderr)
        return 2
    if not has_abs and not has_pct:
        summary["error"] = "need_at_least_one_of_sl_tp"
        _write_summary(args.out, summary)
        print(summary["error"], file=sys.stderr)
        return 2

    try:
        from api.binance_client import (
            BinanceFuturesClient,
            compute_offset_stop_prices,
            validate_protective_triggers,
        )
    except ImportError as e:
        summary["error"] = f"import:{e}"
        _write_summary(args.out, summary)
        print(f"Import error: {e}", file=sys.stderr)
        return 2

    try:
        client = BinanceFuturesClient(testnet=testnet, maker_only=False)
    except Exception as e:
        summary["error"] = str(e)
        _write_summary(args.out, summary)
        print(f"Client init failed: {e}", file=sys.stderr)
        return 2

    pos = client.get_position(args.symbol)
    summary["position"] = pos
    if not pos:
        summary["error"] = "no_open_position"
        _write_summary(args.out, summary)
        print("[skip] no open position for symbol", file=sys.stderr)
        return 1

    entry = float(pos["entry_price"])
    mark = float(pos.get("mark_price") or entry)
    qty = float(pos["quantity"])
    pside = str(pos["side"])

    if has_abs:
        sl_px = args.stop_loss_price
        tp_px = args.take_profit_price
    else:
        sl_px, tp_px = compute_offset_stop_prices(
            entry=entry,
            position_side=pside,
            sl_pct=args.sl_offset_pct,
            tp_pct=args.tp_offset_pct,
        )

    if sl_px is None and tp_px is None:
        summary["error"] = "resolved_no_triggers"
        _write_summary(args.out, summary)
        print(summary["error"], file=sys.stderr)
        return 2

    v_err = validate_protective_triggers(position_side=pside, mark=mark, sl_px=sl_px, tp_px=tp_px)
    if v_err:
        summary["error"] = v_err
        summary["computed"] = {"entry": entry, "mark": mark, "sl_raw": sl_px, "tp_raw": tp_px}
        _write_summary(args.out, summary)
        print(v_err, file=sys.stderr)
        return 1

    sl_rounded = (
        client.round_protective_stop_price(args.symbol, pside, kind="sl", price=sl_px) if sl_px is not None else None
    )
    tp_rounded = (
        client.round_protective_stop_price(args.symbol, pside, kind="tp", price=tp_px) if tp_px is not None else None
    )
    summary["planned"] = {
        "position_side": pside,
        "quantity": qty,
        "entry": entry,
        "mark": mark,
        "stop_loss_stop_price": sl_rounded,
        "take_profit_stop_price": tp_rounded,
    }

    v2 = validate_protective_triggers(position_side=pside, mark=mark, sl_px=sl_rounded, tp_px=tp_rounded)
    if v2:
        summary["error"] = f"post_round_invalid:{v2}"
        _write_summary(args.out, summary)
        print(v2, file=sys.stderr)
        return 1

    if not args.live:
        summary["ok"] = True
        summary["note"] = "dry_run_no_orders"
        _write_summary(args.out, summary)
        print(f"[dry-run] planned TP/SL written to {args.out}")
        return 0

    gate_ok, gate_reason = _run_execution_gate_or_fail(summary, args.out)
    summary["execution_gate"] = {
        "ok": gate_ok,
        "reason": gate_reason or "allow",
    }
    if not gate_ok:
        summary["error"] = gate_reason
        _write_summary(args.out, summary)
        print(f"[blocked] execution gate: {gate_reason}", file=sys.stderr)
        return 2

    sl_order = None
    tp_order = None
    if sl_rounded is not None:
        sl_order = client.place_stop_market_reduce_only(
            args.symbol,
            pside,
            qty,
            sl_rounded,
            working_type=args.working_type,
        )
    if tp_rounded is not None:
        tp_order = client.place_take_profit_market_reduce_only(
            args.symbol,
            pside,
            qty,
            tp_rounded,
            working_type=args.working_type,
        )

    summary["stop_loss"] = (
        {"stop_price": sl_rounded, "order": sl_order} if sl_rounded is not None else None
    )
    summary["take_profit"] = (
        {"stop_price": tp_rounded, "order": tp_order} if tp_rounded is not None else None
    )

    want_sl = sl_rounded is not None
    want_tp = tp_rounded is not None
    def _accepted(order: Any) -> bool:
        if not isinstance(order, dict):
            return False
        return bool(order.get("orderId") or order.get("algoId"))

    ok_sl = (not want_sl) or _accepted(sl_order)
    ok_tp = (not want_tp) or _accepted(tp_order)
    errs: list[str] = []
    if want_sl and not ok_sl:
        errs.append("stop_loss_rejected")
    if want_tp and not ok_tp:
        errs.append("take_profit_rejected")
    if errs:
        summary["error"] = ",".join(errs)
    summary["ok"] = bool(ok_sl and ok_tp)

    _write_summary(args.out, summary)
    _append_protective_audit(summary, args.out)
    if summary["ok"]:
        print(f"[ok] protective orders summary={args.out}")
        return 0
    print(f"[fail] {summary.get('error')} summary={args.out}", file=sys.stderr)
    return 1


def _write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
