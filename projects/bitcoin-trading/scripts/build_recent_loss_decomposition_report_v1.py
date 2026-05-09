#!/usr/bin/env python3
"""Build recent loss decomposition report from realized Binance fills."""
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

DEFAULT_OUT = Path("docs/final/artifacts/recent_loss_decomposition_latest.json")


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


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    wins = [r for r in rows if r["realizedPnl"] > 0]
    losses = [r for r in rows if r["realizedPnl"] < 0]
    side_long = [r for r in rows if str(r.get("positionSide")) == "LONG"]
    side_short = [r for r in rows if str(r.get("positionSide")) == "SHORT"]
    side_long_loss = [r for r in side_long if r["realizedPnl"] < 0]
    side_short_loss = [r for r in side_short if r["realizedPnl"] < 0]

    max_loss_streak = 0
    cur = 0
    for r in rows:
        if r["realizedPnl"] < 0:
            cur += 1
            max_loss_streak = max(max_loss_streak, cur)
        else:
            cur = 0

    return {
        "realized_rows_used": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round((len(wins) / n), 6) if n else 0.0,
        "total_realized_pnl": round(sum(r["realizedPnl"] for r in rows), 6),
        "avg_win": round(sum(r["realizedPnl"] for r in wins) / len(wins), 6) if wins else 0.0,
        "avg_loss_abs": round(abs(sum(r["realizedPnl"] for r in losses)) / len(losses), 6) if losses else 0.0,
        "max_loss_streak": max_loss_streak,
        "by_position_side": {
            "LONG": {
                "count": len(side_long),
                "loss_count": len(side_long_loss),
                "loss_sum_abs": round(abs(sum(r["realizedPnl"] for r in side_long_loss)), 6),
            },
            "SHORT": {
                "count": len(side_short),
                "loss_count": len(side_short_loss),
                "loss_sum_abs": round(abs(sum(r["realizedPnl"] for r in side_short_loss)), 6),
            },
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Loss decomposition from recent realized fills.")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--mainnet", action="store_true")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    from api.binance_client import BinanceFuturesClient

    c = BinanceFuturesClient(testnet=not args.mainnet, maker_only=False)
    fills = c.get_recent_fills(args.symbol, limit=max(20, args.limit))
    realized_rows: list[dict[str, Any]] = []
    for f in fills:
        if not isinstance(f, dict):
            continue
        rp = _to_float(f.get("realizedPnl"), 0.0)
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

    # older -> newer for streak semantics
    realized_rows_sorted = sorted(realized_rows, key=lambda r: int(r.get("time") or 0))
    summary = _summarize(realized_rows_sorted)
    payload = {
        "schema": "recent_loss_decomposition_v1",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "symbol": args.symbol,
        "mainnet": bool(args.mainnet),
        "fills_scanned": len(fills),
        "summary": summary,
        "latest_realized_rows": list(reversed(realized_rows_sorted[-20:])),
    }
    _write(args.out, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
