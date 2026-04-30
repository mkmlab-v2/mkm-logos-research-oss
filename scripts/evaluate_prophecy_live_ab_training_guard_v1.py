#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "prophecy_live_ab_training_policy_v1_latest.json"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "prophecy_live_ab_summary_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_live_ab_training_guard_eval_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate live A/B training guard readiness.")
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = _load_json(args.policy_json)
    summary = _load_json(args.summary_json)

    status = str(summary.get("status", "UNKNOWN"))
    env = summary.get("environment") if isinstance(summary.get("environment"), dict) else {}
    snapshot = summary.get("exchange_snapshot_24h") if isinstance(summary.get("exchange_snapshot_24h"), dict) else {}
    fills_24h = _safe_int(snapshot.get("fills_count"))
    trading_enabled = bool(env.get("status_enable_trading", False))
    is_testnet = bool(env.get("status_testnet", True))

    min_recent_trades = _safe_int((policy.get("online_update_guard") or {}).get("min_recent_trades"))
    hard_stop_if_insufficient = bool((policy.get("hard_stop") or {}).get("if_data_insufficient", True))

    blockers = []
    if status == "INSUFFICIENT_DATA" and hard_stop_if_insufficient:
        blockers.append("insufficient_data_status")
    if fills_24h < min_recent_trades:
        blockers.append("fills_24h_below_min_recent_trades")
    if not trading_enabled:
        blockers.append("trading_not_enabled")

    decision = "HOLD_TRAINING_GUARD"
    if not blockers and is_testnet:
        decision = "ALLOW_TESTNET_AB_TRAINING"
    elif not blockers and not is_testnet:
        decision = "ALLOW_MICRO_LIVE_AB_TRAINING_WITH_HUMAN_SIGNOFF"

    out = {
        "schema": "prophecy_live_ab_training_guard_eval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "policy_json": str(args.policy_json),
            "summary_json": str(args.summary_json),
        },
        "summary_snapshot": {
            "status": status,
            "status_symbol": env.get("status_symbol"),
            "status_testnet": is_testnet,
            "status_enable_trading": trading_enabled,
            "fills_count_24h": fills_24h,
        },
        "policy_thresholds": {
            "min_recent_trades": min_recent_trades,
            "max_updates_per_day": _safe_int((policy.get("online_update_guard") or {}).get("max_updates_per_day")),
            "max_consecutive_losses_per_arm": _safe_int((policy.get("loss_streak_kill_switch") or {}).get("max_consecutive_losses_per_arm")),
        },
        "decision": {
            "status": decision,
            "blocker_count": len(blockers),
            "blockers": blockers,
        },
        "note": "This evaluation gates training-oriented A/B operation only; no automatic production promotion.",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
