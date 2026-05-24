#!/usr/bin/env python3
"""24h live PnL vs prophecy rollback policy + GO/gates (read-only by default)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sum_trade_window(doc: dict[str, Any]) -> dict[str, float]:
    rows = list(doc.get("treatment") or []) + list(doc.get("control") or [])
    realized = 0.0
    commission = 0.0
    for r in rows:
        realized += _num(r.get("realized_pnl"))
        commission += _num(r.get("commission"))
    net = realized - commission
    return {
        "trade_count": float(len(rows)),
        "realized_pnl_sum": realized,
        "commission_sum": commission,
        "net_pnl_usdt": net,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prophecy live rollback readiness check.")
    p.add_argument(
        "--trade-window-json",
        default="projects/bitcoin-trading/exports/cursor_trade_history/cursor_trade_history_latest_24h.json",
    )
    p.add_argument(
        "--rollback-policy-json",
        default="docs/final/artifacts/prophecy_live_rollback_policy_v1_latest.json",
    )
    p.add_argument(
        "--go-json",
        default="docs/final/artifacts/trading_go_no_go_latest.json",
    )
    p.add_argument(
        "--gates-json",
        default="reports/prophecy_promotion_gates_recommended_chain_v1_latest.json",
    )
    p.add_argument(
        "--reference-usdt",
        type=float,
        default=0.0,
        help="Denominator for loss %% (0 = use env MKM_LIVE_ROLLBACK_REFERENCE_USDT or 500).",
    )
    p.add_argument(
        "--out-json",
        default="reports/prophecy_live_rollback_check_v1_latest.json",
    )
    p.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit 2 when rollback_triggered.",
    )
    return p.parse_args()


def main() -> int:
    import os

    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    trade_path = (root / args.trade_window_json).resolve()
    policy_path = (root / args.rollback_policy_json).resolve()
    go_path = (root / args.go_json).resolve()
    gates_path = (root / args.gates_json).resolve()
    out_path = (root / args.out_json).resolve()

    breaches: list[str] = []
    notes: list[str] = []

    if not trade_path.is_file():
        breaches.append("missing_trade_window")
        trade_stats = {"trade_count": 0, "net_pnl_usdt": 0.0}
    else:
        trade_stats = _sum_trade_window(_load_json(trade_path))

    max_loss_pct = 2.0
    if policy_path.is_file():
        pol = _load_json(policy_path)
        max_loss_pct = _num((pol.get("policy") or {}).get("max_daily_loss_pct"), 2.0)

    ref = args.reference_usdt
    if ref <= 0:
        ref = _num(os.environ.get("MKM_LIVE_ROLLBACK_REFERENCE_USDT"), 0.0)
    if ref <= 0:
        ref = 500.0

    net = trade_stats["net_pnl_usdt"]
    loss_pct = 0.0
    if net < 0 and ref > 0:
        loss_pct = abs(net) / ref * 100.0
    if loss_pct >= max_loss_pct:
        breaches.append(f"daily_loss_pct_ge_max:{loss_pct:.4f}>={max_loss_pct}")

    go_no_go = "UNKNOWN"
    if go_path.is_file():
        go = _load_json(go_path)
        go_no_go = str(go.get("go_no_go") or "UNKNOWN")
        if go_no_go != "GO":
            breaches.append(f"go_no_go_{go_no_go}")
    else:
        notes.append("missing_go_json")

    gates_ok = None
    if gates_path.is_file():
        gates = _load_json(gates_path)
        gates_ok = bool(gates.get("combined_all_passed"))
        if not gates_ok:
            breaches.append("promotion_gates_not_all_passed")
    else:
        notes.append("missing_gates_json")

    rollback_triggered = len(breaches) > 0
    result = {
        "schema": "prophecy_live_rollback_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "inputs": {
            "trade_window_json": str(trade_path),
            "rollback_policy_json": str(policy_path),
            "go_json": str(go_path),
            "gates_json": str(gates_path),
            "reference_usdt": ref,
        },
        "trade_stats": trade_stats,
        "observed": {
            "daily_loss_pct_vs_reference": round(loss_pct, 6),
            "max_daily_loss_pct": max_loss_pct,
            "go_no_go": go_no_go,
            "combined_all_passed": gates_ok,
        },
        "rollback_triggered": rollback_triggered,
        "breaches": breaches,
        "notes": notes,
        "recommended_actions": (
            ["disable_live_trigger_immediately", "human_review_required"]
            if rollback_triggered
            else []
        ),
        "constraints": {
            "auto_disable_live": False,
            "use_apply_disable_switch_on_ps1": True,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"rollback_triggered={rollback_triggered} loss_pct={loss_pct:.4f} net_usdt={net:.4f}")
    if args.strict_exit and rollback_triggered:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
