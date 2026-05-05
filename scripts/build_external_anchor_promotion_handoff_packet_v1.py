#!/usr/bin/env python3
"""Build one-file handoff packet for external anchor promotion/recovery decisions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROMOTION = ART / "external_bible_anchor_tier1_promotion_candidates_latest.json"
DEFAULT_PROMOTED = ART / "external_bible_anchor_tier1_promoted_latest.json"
DEFAULT_RECOVERY = ART / "external_bible_anchor_recovery_candidates_latest.json"
DEFAULT_SUSTAIN = ART / "external_bible_anchor_promotion_sustain_gate_latest.json"
DEFAULT_POLICY = ART / "external_bible_anchor_operating_policy_latest.json"
DEFAULT_WEEKLY_AB = ART / "external_bible_anchor_weekly_ab_report_latest.json"
DEFAULT_POLICY_STAGE_DRILL = ART / "external_bible_anchor_policy_stage_drill_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_promotion_handoff_packet_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promotion-json", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--promoted-json", type=Path, default=DEFAULT_PROMOTED)
    ap.add_argument("--recovery-json", type=Path, default=DEFAULT_RECOVERY)
    ap.add_argument("--sustain-json", type=Path, default=DEFAULT_SUSTAIN)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--weekly-ab-json", type=Path, default=DEFAULT_WEEKLY_AB)
    ap.add_argument("--policy-stage-drill-json", type=Path, default=DEFAULT_POLICY_STAGE_DRILL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    promotion = _read_json(args.promotion_json)
    promoted = _read_json(args.promoted_json)
    recovery = _read_json(args.recovery_json)
    sustain = _read_json(args.sustain_json)
    policy = _read_json(args.policy_json)
    weekly_ab = _read_json(args.weekly_ab_json)
    stage_drill = _read_json(args.policy_stage_drill_json)

    promotion_status = str(promotion.get("status") or "")
    promoted_status = str(promoted.get("status") or "")
    promoted_count = int(promoted.get("promoted_count") or 0)
    already_promoted = promoted_status in {"PROMOTED_TIER1_CANDIDATES", "PROMOTED_TIER1_CANDIDATES_LATCHED"} and promoted_count > 0
    recovery_status = str(recovery.get("status") or "")
    sustain_status = str(sustain.get("status") or "")
    policy_action = str(policy.get("effective_action") or "")
    policy_stage = str(policy.get("policy_stage") or "")
    weekly_ab_status = str(((weekly_ab.get("summary") or {}).get("status")) or "")
    drill_ok = len(stage_drill.get("results") or []) >= 3

    promotion_count = len(promotion.get("promotion_candidates") or [])
    recovery_count = len(recovery.get("recovery_candidates") or [])
    pass_rate_delta = (weekly_ab.get("summary") or {}).get("pass_rate_delta_adopt_minus_monitor")

    recommendation = "hold_monitor"
    promotion_lane = "none"
    if sustain_status == "DOWNGRADE_TRIGGER" and recovery_status == "RECOVERY_READY_FOR_REVIEW":
        recommendation = "request_recovery_manual_signoff"
        promotion_lane = "recovery_review"
    elif already_promoted and policy_action in {"adopt_limited", "adopt_limited_strict"}:
        recommendation = "keep_operating_policy_no_new_signoff"
        promotion_lane = "already_promoted"
    elif already_promoted and policy_action == "monitor_only":
        recommendation = "promoted_labels_present_but_policy_monitor_only_review_chain"
        promotion_lane = "already_promoted_rollback_or_hold"
    elif promotion_status == "READY_FOR_HUMAN_REVIEW" and not already_promoted:
        recommendation = "request_tier1_manual_promotion_signoff"
        promotion_lane = "human_review_queue"
    elif sustain_status == "MATURE" and policy_action in {"adopt_limited", "adopt_limited_strict"}:
        recommendation = "keep_adopt_limited"
        promotion_lane = "mature_operating"

    readiness_checks = {
        "weekly_ab_ready": weekly_ab_status in {"PASS", "WARMUP"},
        "policy_stage_drill_ready": drill_ok,
        "policy_action_present": bool(policy_action),
    }
    packet_status = "READY" if all(readiness_checks.values()) else "INCOMPLETE"

    out = {
        "schema": "external_bible_anchor_promotion_handoff_packet_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "promotion_json": str(args.promotion_json).replace("\\", "/"),
            "promoted_json": str(args.promoted_json).replace("\\", "/"),
            "recovery_json": str(args.recovery_json).replace("\\", "/"),
            "sustain_json": str(args.sustain_json).replace("\\", "/"),
            "policy_json": str(args.policy_json).replace("\\", "/"),
            "weekly_ab_json": str(args.weekly_ab_json).replace("\\", "/"),
            "policy_stage_drill_json": str(args.policy_stage_drill_json).replace("\\", "/"),
        },
        "summary": {
            "packet_status": packet_status,
            "recommendation": recommendation,
            "promotion_lane": promotion_lane,
            "promoted_status": promoted_status,
            "already_promoted": already_promoted,
            "promotion_status": promotion_status,
            "promotion_candidate_count": promotion_count,
            "recovery_status": recovery_status,
            "recovery_candidate_count": recovery_count,
            "sustain_status": sustain_status,
            "policy_effective_action": policy_action,
            "policy_stage": policy_stage,
            "weekly_ab_status": weekly_ab_status,
            "weekly_ab_pass_rate_delta": pass_rate_delta,
            "policy_stage_drill_scenarios": len(stage_drill.get("results") or []),
        },
        "readiness_checks": readiness_checks,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "packet_status": packet_status,
                "recommendation": recommendation,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
