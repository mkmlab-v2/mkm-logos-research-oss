#!/usr/bin/env python3
"""Check Binance USD-M protective order coverage for current position.

Reports whether the active position has both SL/TP conditional orders
(`STOP_MARKET`, `TAKE_PROFIT_MARKET`) on the matching `positionSide`.
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

DEFAULT_OUT = Path("docs/final/artifacts/protective_order_coverage_latest.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_side(position_side: str) -> str:
    s = str(position_side or "").upper()
    if s in {"LONG", "SHORT"}:
        return s
    return ""


def _required_close_side(position_side: str) -> str:
    return "SELL" if position_side == "LONG" else "BUY"


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Protective order coverage check (Binance USD-M).")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--mainnet", action="store_true", help="Default is testnet when omitted.")
    ap.add_argument("--min-qty-ratio", type=float, default=0.95, help="Required covered qty ratio per SL/TP.")
    ap.add_argument("--strict-exit", action="store_true", help="Exit 1 when uncovered.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    testnet = not args.mainnet
    payload: dict[str, Any] = {
        "schema": "binance_usdm_protective_coverage_v1",
        "generated_at_utc": _utc_now(),
        "symbol": args.symbol,
        "testnet": testnet,
        "ok": False,
        "status": "unknown",
        "position": None,
        "coverage": None,
        "error": None,
    }

    try:
        from api.binance_client import BinanceFuturesClient
    except ImportError as e:
        payload["status"] = "import_error"
        payload["error"] = str(e)
        _write(args.out, payload)
        print(payload["error"], file=sys.stderr)
        return 2

    try:
        client = BinanceFuturesClient(testnet=testnet, maker_only=False)
        pos = client.get_position(args.symbol)
        payload["position"] = pos
        if not pos:
            payload["ok"] = True
            payload["status"] = "no_open_position"
            _write(args.out, payload)
            print("no_open_position")
            return 0

        pside = _norm_side(pos.get("side"))
        qty = abs(_to_float(pos.get("quantity")))
        close_side = _required_close_side(pside)
        orders = client.get_open_orders(args.symbol)

        sl_orders: list[dict[str, Any]] = []
        tp_orders: list[dict[str, Any]] = []
        for o in orders:
            if not isinstance(o, dict):
                continue
            if _norm_side(o.get("positionSide")) != pside:
                continue
            if str(o.get("side") or "").upper() != close_side:
                continue
            typ = str(o.get("type") or "").upper()
            if typ == "STOP_MARKET":
                sl_orders.append(o)
            elif typ == "TAKE_PROFIT_MARKET":
                tp_orders.append(o)

        sl_qty = sum(abs(_to_float(o.get("origQty") or o.get("quantity"))) for o in sl_orders)
        tp_qty = sum(abs(_to_float(o.get("origQty") or o.get("quantity"))) for o in tp_orders)
        min_ratio = max(0.0, min(1.5, float(args.min_qty_ratio)))
        need_qty = qty * min_ratio

        sl_ok = bool(sl_orders) and sl_qty >= need_qty
        tp_ok = bool(tp_orders) and tp_qty >= need_qty

        # Fallback evidence for conditional algo orders that may not appear in open-orders endpoint.
        if not (sl_ok and tp_ok):
            latest_exec = _read_json(Path("reports/binance_usdm_single_order/protective_orders_latest.json"))
            if not latest_exec:
                latest_exec = _read_json(Path("docs/final/artifacts/protective_orders_latest.json"))
            lpos = latest_exec.get("position") if isinstance(latest_exec.get("position"), dict) else {}
            lsl = latest_exec.get("stop_loss") if isinstance(latest_exec.get("stop_loss"), dict) else {}
            ltp = latest_exec.get("take_profit") if isinstance(latest_exec.get("take_profit"), dict) else {}
            lsl_o = lsl.get("order") if isinstance(lsl.get("order"), dict) else {}
            ltp_o = ltp.get("order") if isinstance(ltp.get("order"), dict) else {}
            same_symbol = str(latest_exec.get("symbol") or "").upper() == str(args.symbol).upper()
            same_side = _norm_side(lpos.get("side")) == pside
            lqty = abs(_to_float(lpos.get("quantity")))
            qty_ok = lqty >= need_qty if lqty > 0 else False
            sl_present = bool(lsl_o.get("algoId") or lsl_o.get("orderId"))
            tp_present = bool(ltp_o.get("algoId") or ltp_o.get("orderId"))
            if same_symbol and same_side and qty_ok and sl_present and tp_present:
                sl_ok = True
                tp_ok = True

        ok = sl_ok and tp_ok

        payload["coverage"] = {
            "position_side": pside,
            "position_qty": qty,
            "required_close_side": close_side,
            "min_qty_ratio": min_ratio,
            "required_qty": need_qty,
            "sl_order_count": len(sl_orders),
            "tp_order_count": len(tp_orders),
            "sl_total_orig_qty": sl_qty,
            "tp_total_orig_qty": tp_qty,
            "sl_ok": sl_ok,
            "tp_ok": tp_ok,
        }
        payload["ok"] = ok
        payload["status"] = "covered" if ok else "uncovered"
        _write(args.out, payload)
        print(payload["status"])
        if args.strict_exit and not ok:
            return 1
        return 0
    except Exception as e:  # noqa: BLE001
        payload["status"] = "runtime_error"
        payload["error"] = str(e)
        _write(args.out, payload)
        print(payload["error"], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
