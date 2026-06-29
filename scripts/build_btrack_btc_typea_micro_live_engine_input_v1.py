#!/usr/bin/env python3
"""Build non-executing engine handoff for B-track Type-A micro-live experiment."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
POLICY = ROOT / "docs/final/artifacts/btrack_btc_typea_micro_live_policy_v1.json"
APPROVAL = ROOT / "docs/final/artifacts/btrack_btc_typea_micro_live_human_approval_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btc_limited_live_engine_input_from_btrack_typea_v1_latest.json"
SIGNAL_LOG = ROOT / "reports/btrack_phase1_micro_live_signal_log_v1.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _latest_btc_row(score: dict[str, Any]) -> dict[str, Any] | None:
    btc_rows = [
        r
        for r in (score.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "btc"
    ]
    if not btc_rows:
        return None
    return max(btc_rows, key=lambda r: str(r.get("eval_date") or ""))


def _side_hint(direction: str) -> str:
    d = direction.strip().lower()
    if d == "bull":
        return "BUY"
    if d == "bear":
        return "SELL"
    return "HOLD"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=SCORE)
    ap.add_argument("--policy-json", type=Path, default=POLICY)
    ap.add_argument("--approval-json", type=Path, default=APPROVAL)
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--signal-log", type=Path, default=SIGNAL_LOG)
    ap.add_argument("--approve-submit", action="store_true")
    ap.add_argument("--live", action="store_true", help="Emit dry_run=false in payload metadata.")
    args = ap.parse_args(argv)

    approval = _load(args.approval_json)
    policy = _load(args.policy_json)
    score = _load(args.score_json)
    row = _latest_btc_row(score)
    if not row:
        raise SystemExit("no btc rows in score json")

    approved = str(approval.get("decision") or "") == "APPROVED_BTRACK_TYPEA_MICRO_LIVE_EXPERIMENT"
    direction = str(row.get("predicted_direction") or "neutral").lower()
    side_hint = _side_hint(direction)
    submit_ok = bool(args.approve_submit) and approved and side_hint in {"BUY", "SELL"}
    status = "READY_FOR_ENGINE_SUBMIT" if submit_ok else "HOLD_FOR_HUMAN_REVIEW"

    guard_meta = (score.get("meta") or {}).get("btc_typea_guard_v1") if isinstance(score.get("meta"), dict) else {}

    payload = {
        "schema": "btc_limited_live_engine_input_v1",
        "variant": "btrack_typea_micro_live_v1",
        "generated_at_utc": _now(),
        "symbol": args.symbol,
        "status": status,
        "dry_run": not bool(args.live),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "source": {
            "score_json": str(args.score_json.resolve()),
            "policy_json": str(args.policy_json.resolve()),
            "approval_json": str(args.approval_json.resolve()) if args.approval_json.is_file() else None,
        },
        "guards": {
            "micro_live_approved": approved,
            "approve_submit_flag": bool(args.approve_submit),
            "typea_guard_applied": bool(row.get("typea_guard_applied")),
            "direction_tradable": side_hint in {"BUY", "SELL"},
        },
        "btrack_signal": {
            "eval_date": row.get("eval_date"),
            "predicted_direction": direction,
            "side_hint": side_hint,
            "typea_guard_policy_id": row.get("typea_guard_policy_id"),
            "guard_meta": guard_meta if isinstance(guard_meta, dict) else {},
        },
        "engine_input": {
            "signal_type": "btrack_typea_prophecy_micro_live_v1",
            "side_hint": side_hint,
            "size_usd": policy.get("size_usd", 35),
            "max_consecutive_losses": policy.get("max_consecutive_losses", 4),
            "max_drawdown_pct": policy.get("max_drawdown_pct", 3.0),
            "max_trades_per_day": policy.get("max_trades_per_day", 4),
            "auto_scale_up": False,
            "auto_bridge_enabled": False,
            "auto_live_trigger_enabled": False,
            "candidate_params": {
                "source": "btrack_typea_micro_live",
                "direction_bias": direction,
                "max_position_size": policy.get("max_position_size", 0.06),
            },
        },
        "action": "submit_to_engine_queue" if submit_ok else "wait_for_human_approval",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()}")
    print(f"status={status} side_hint={side_hint} eval_date={row.get('eval_date')}")

    log_row = {
        "logged_at_utc": _now(),
        "eval_date": row.get("eval_date"),
        "predicted_direction": direction,
        "side_hint": side_hint,
        "engine_status": status,
        "size_usd": policy.get("size_usd"),
    }
    args.signal_log.parent.mkdir(parents=True, exist_ok=True)
    with args.signal_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(log_row, ensure_ascii=False) + "\n")
    print(f"APPENDED: {args.signal_log.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
