# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.5}
# Balance: 93
# Purpose: Build policy artifact for price-output unlock and relock guardrails.
# Keywords: track_a, price_output, unlock, relock, policy
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_price_output_unlock_policy_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_payload(
    go_nogo: dict[str, Any],
    policy_floor: dict[str, Any],
) -> dict[str, Any]:
    current = go_nogo.get("result") or {}
    snapshot = go_nogo.get("snapshot") or {}
    policy_decision = str(policy_floor.get("decision") or "")

    unlock_conditions = {
        "high_reliability_decision_non_hold_consecutive": 2,
        "chronos_holdout_direction_match_rate_min_pct": 50.0,
        "chronos_holdout_average_error_percentage_max": 5.0,
        "paper_strict_min_weeks_before_scaled": 4,
        "required_stage_before_unlock": "S2_PAPER_STRICT",
    }
    relock_triggers = [
        "high_reliability_decision_returns_hold",
        "price_output_locked_true_reasserted",
        "chronos_holdout_direction_match_rate_below_45_pct",
        "daily_loss_cap_breach",
        "operator_stop_command",
    ]

    return {
        "schema": "a_track_price_output_unlock_policy_v1",
        "generated_at_utc": _now_utc(),
        "status": "READY_FOR_SIGNOFF",
        "research_only": False,
        "inputs": {
            "a_track_go_nogo_status": "docs/final/artifacts/a_track_go_nogo_status_latest.json",
            "track_a_policy_floor_decision": "docs/final/artifacts/track_a_policy_floor_decision_v1.json",
        },
        "current_snapshot": {
            "overall_go_no_go": current.get("overall_go_no_go"),
            "recommended_stage": current.get("recommended_stage"),
            "high_reliability_decision": snapshot.get("high_reliability_decision"),
            "price_output_locked": snapshot.get("price_output_locked"),
            "policy_floor_decision": policy_decision,
        },
        "unlock_policy": {
            "mode": "evidence_based_no_bypass",
            "conditions": unlock_conditions,
            "decision_rule": "all_conditions_must_pass",
            "operator_signoff_required": True,
        },
        "relock_policy": {
            "triggers": relock_triggers,
            "action_on_trigger": "immediate_hold_and_stage_rollback_to_S1_SHADOW",
            "auto_alert_required": True,
        },
        "notes_ko": [
            "단발 성능이 아닌 연속성(주차)과 재현성 기준으로 잠금 해제를 판단한다.",
            "승인 전까지는 price output unlock을 실제 runtime에 반영하지 않는다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build A-track price-output unlock policy artifact.")
    ap.add_argument(
        "--go-nogo",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json",
    )
    ap.add_argument(
        "--policy-floor",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_decision_v1.json",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    go_nogo_path = args.go_nogo if args.go_nogo.is_absolute() else ROOT / args.go_nogo
    policy_path = args.policy_floor if args.policy_floor.is_absolute() else ROOT / args.policy_floor
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    payload = build_payload(
        go_nogo=_load_json(go_nogo_path),
        policy_floor=_load_json(policy_path),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"status: {payload['status']}")
    print(f"operator_signoff_required: {payload['unlock_policy']['operator_signoff_required']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
