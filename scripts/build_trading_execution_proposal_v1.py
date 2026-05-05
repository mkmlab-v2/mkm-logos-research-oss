#!/usr/bin/env python3
"""Build trading execution proposal artifact (disk SSOT, no order execution)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RISK = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
DEFAULT_GATE = ROOT / "reports" / "poc_binance_signal_webhook" / "conditional_gate_latest.json"
DEFAULT_OUT = ROOT / "reports" / "trading_execution_proposal_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--side", choices=("BUY", "SELL"), default="BUY")
    ap.add_argument("--qty", type=float, default=0.001)
    ap.add_argument("--leverage", type=int, default=2)
    ap.add_argument("--target", choices=("mainnet_small", "testnet_live"), default="mainnet_small")
    ap.add_argument("--risk-json", type=Path, default=DEFAULT_RISK)
    ap.add_argument("--gate-summary", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--note", default="Operator-reviewed execution proposal.")
    args = ap.parse_args()

    risk_path = args.risk_json if args.risk_json.is_absolute() else (ROOT / args.risk_json)
    gate_path = args.gate_summary if args.gate_summary.is_absolute() else (ROOT / args.gate_summary)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    risk = _read_json(risk_path) or {}
    gate = _read_json(gate_path) or {}
    generated_at = _utc_now()
    proposal_id = f"trade-proposal-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    doc: dict[str, Any] = {
        "schema": "trading_execution_proposal_v1",
        "proposal_id": proposal_id,
        "generated_at_utc": generated_at,
        "target": args.target,
        "intent_summary": f"{args.target} {args.side} {args.qty} {args.symbol} x{args.leverage}",
        "order_intent": {
            "symbol": args.symbol,
            "side": args.side,
            "qty": args.qty,
            "leverage": args.leverage,
            "mainnet": args.target == "mainnet_small",
        },
        "inputs": {
            "risk_json_path": str(risk_path),
            "risk_mode": (risk.get("trinity_governor") or {}).get("mode") if isinstance(risk.get("trinity_governor"), dict) else None,
            "risk_final_action_allowed": (risk.get("governance_bridge") or {}).get("final_action_allowed")
            if isinstance(risk.get("governance_bridge"), dict)
            else None,
            "gate_summary_path": str(gate_path),
            "gate_ok": gate.get("gate_ok"),
            "gate_reason": gate.get("gate_reason"),
        },
        "operator_note": args.note,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"PROPOSAL_ID={proposal_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

