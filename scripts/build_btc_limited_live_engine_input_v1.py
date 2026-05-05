#!/usr/bin/env python3
"""Adapt limited-live candidate artifact into BTC engine input payload.

This adapter is non-executing and writes only a JSON handoff payload.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATE = ART / "btc_top1_limited_live_candidate_latest.json"
DEFAULT_SIGNOFF = ART / "promotion_signoff_decision_latest.json"
DEFAULT_OUT = ART / "btc_limited_live_engine_input_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-json", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--symbol", type=str, default="BTCUSDT")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", action="store_true", help="Emit non-dry-run payload (still non-executing).")
    ap.add_argument("--approve-submit", action="store_true", help="Require explicit human approval")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.live:
        args.dry_run = False

    candidate = _read(args.candidate_json)
    signoff = _read(args.signoff_json) if args.signoff_json.is_file() else {}

    cand_ok = bool((candidate.get("decision") or {}).get("tradable_candidate"))
    signoff_ok = str(((signoff.get("decision") or {}).get("status") or "")).upper() == "APPROVE"
    mode_ok = str(((signoff.get("decision") or {}).get("mode") or "")).lower() in {
        "limited_live_deployment",
        "s4_limited_live",
    }

    approved_to_submit = bool(args.approve_submit) and cand_ok and signoff_ok and mode_ok
    status = "READY_FOR_ENGINE_SUBMIT" if approved_to_submit else "HOLD_FOR_HUMAN_REVIEW"

    policy = candidate.get("limited_live_policy") or {}
    payload = {
        "schema": "btc_limited_live_engine_input_v1",
        "generated_at_utc": _now(),
        "symbol": args.symbol,
        "status": status,
        "dry_run": bool(args.dry_run),
        "source": {
            "candidate_json": str(args.candidate_json.resolve()),
            "signoff_json": str(args.signoff_json.resolve()) if args.signoff_json.is_file() else None,
        },
        "guards": {
            "candidate_tradable": cand_ok,
            "signoff_approve": signoff_ok,
            "signoff_mode_limited_live": mode_ok,
            "approve_submit_flag": bool(args.approve_submit),
        },
        "engine_input": {
            "signal_type": "fusion_prophecy_top1_limited_live",
            "side_hint": "derived_by_engine",
            "size_usd": policy.get("limited_position_usd"),
            "max_consecutive_losses": policy.get("max_consecutive_losses"),
            "max_drawdown_pct": policy.get("max_drawdown_pct"),
            "auto_scale_up": False,
            "auto_bridge_enabled": False,
            "auto_live_trigger_enabled": False,
            "candidate_params": (candidate.get("candidate") or {}).get("params", {}),
            "candidate_metrics": (candidate.get("candidate") or {}).get("metrics", {}),
        },
        "action": "submit_to_engine_queue" if approved_to_submit else "wait_for_human_approval",
    }
    tbp = candidate.get("tie_break_policy")
    if isinstance(tbp, dict):
        payload["tie_break_policy"] = tbp

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
