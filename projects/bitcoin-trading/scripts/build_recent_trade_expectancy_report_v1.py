#!/usr/bin/env python3
"""Build a compact expectancy report from recent Binance futures fills."""
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

DEFAULT_OUT = Path("docs/final/artifacts/recent_trade_expectancy_latest.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Recent trade expectancy report from realizedPnL fills.")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--mainnet", action="store_true")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    try:
        from api.binance_client import BinanceFuturesClient
    except ImportError as e:
        payload = {
            "schema": "recent_trade_expectancy_v1",
            "generated_at_utc": _utc_now(),
            "ok": False,
            "error": f"import:{e}",
        }
        _write(args.out, payload)
        print(payload["error"], file=sys.stderr)
        return 2

    c = BinanceFuturesClient(testnet=not args.mainnet, maker_only=False)
    fills = c.get_recent_fills(args.symbol, limit=max(10, args.limit))
    realized_rows: list[dict[str, Any]] = []
    for f in fills:
        if not isinstance(f, dict):
            continue
        rp = _to_float(f.get("realizedPnl"), 0.0)
        # realizedPnl 0 rows are mostly entries/partials; skip for expectancy of closed outcomes
        if abs(rp) < 1e-12:
            continue
        realized_rows.append(
            {
                "time": f.get("time"),
                "side": f.get("side"),
                "positionSide": f.get("positionSide"),
                "qty": _to_float(f.get("qty") or f.get("executedQty"), 0.0),
                "price": _to_float(f.get("price"), 0.0),
                "realizedPnl": rp,
            }
        )

    n = len(realized_rows)
    wins = [r for r in realized_rows if r["realizedPnl"] > 0]
    losses = [r for r in realized_rows if r["realizedPnl"] < 0]
    n_win = len(wins)
    n_loss = len(losses)
    win_rate = (n_win / n) if n > 0 else 0.0
    avg_win = (sum(r["realizedPnl"] for r in wins) / n_win) if n_win > 0 else 0.0
    avg_loss_abs = (abs(sum(r["realizedPnl"] for r in losses)) / n_loss) if n_loss > 0 else 0.0
    expectancy = (win_rate * avg_win) - ((1.0 - win_rate) * avg_loss_abs)
    total_realized = sum(r["realizedPnl"] for r in realized_rows)

    payload = {
        "schema": "recent_trade_expectancy_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "symbol": args.symbol,
        "mainnet": bool(args.mainnet),
        "sample": {
            "fills_scanned": len(fills),
            "realized_rows_used": n,
        },
        "metrics": {
            "win_rate": round(win_rate, 6),
            "avg_win": round(avg_win, 6),
            "avg_loss_abs": round(avg_loss_abs, 6),
            "expectancy_per_realized_fill": round(expectancy, 6),
            "total_realized_pnl": round(total_realized, 6),
            "wins": n_win,
            "losses": n_loss,
        },
        "latest_realized_rows": realized_rows[:20],
    }
    _write(args.out, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
