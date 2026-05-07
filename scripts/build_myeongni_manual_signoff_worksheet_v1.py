#!/usr/bin/env python3
"""Build a manual sign-off worksheet draft for myeongni promotion."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_PROMOTION_GATE = ART / "myeongni_promotion_gate_latest.json"
DEFAULT_MANUAL_LOCK = ART / "myeongni_manual_promotion_decision_lock_latest.json"
DEFAULT_READINESS = ART / "myeongni_commercialization_readiness_packet_latest.json"
DEFAULT_STAGE2_REALSET_GATE = ART / "myeongni_stage2_realset_gate_latest.json"
DEFAULT_SHADOW_GOV = ART / "myeongni_shadow_governance_latest.json"
DEFAULT_PENALTY_DAILY = ART / "lens_penalty_daily_latest.json"
DEFAULT_OUT = ART / "myeongni_manual_signoff_worksheet_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_PROMOTION_GATE)
    ap.add_argument("--manual-lock", type=Path, default=DEFAULT_MANUAL_LOCK)
    ap.add_argument("--readiness", type=Path, default=DEFAULT_READINESS)
    ap.add_argument("--stage2-realset-gate", type=Path, default=DEFAULT_STAGE2_REALSET_GATE)
    ap.add_argument("--shadow-governance", type=Path, default=DEFAULT_SHADOW_GOV)
    ap.add_argument("--penalty-daily", type=Path, default=DEFAULT_PENALTY_DAILY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate = _read_json(args.promotion_gate)
    lock_doc = _read_json(args.manual_lock)
    readiness = _read_json(args.readiness)
    realset_gate = _read_json(args.stage2_realset_gate)
    shadow_gov = _read_json(args.shadow_governance)
    penalty_daily = _read_json(args.penalty_daily)

    gate_pass = str(gate.get("status") or "").upper() == "PASS"
    go_manual = bool(gate.get("go_for_manual_signoff"))
    lock_approved = str(lock_doc.get("final_decision") or "").lower() == "approved"
    readiness_ready = str(readiness.get("readiness") or "").upper() == "READY"
    realset_pass = bool(realset_gate.get("pass"))
    realset_count = int(realset_gate.get("real_count") or 0)

    policy = gate.get("policy") if isinstance(gate.get("policy"), dict) else {}
    auto_bridge_off = bool(policy.get("track_b_to_a_auto_bridge") is False)
    auto_live_off = bool(policy.get("live_trigger_auto_enabled") is False)
    human_required = bool(policy.get("human_signoff_required") is True)

    shadow_decision = str(shadow_gov.get("decision") or "")
    shadow_blockers = shadow_gov.get("blockers") if isinstance(shadow_gov.get("blockers"), list) else []
    shadow_warnings = shadow_gov.get("warnings") if isinstance(shadow_gov.get("warnings"), list) else []
    penalty_summary = penalty_daily.get("summary") if isinstance(penalty_daily.get("summary"), dict) else {}
    penalty_mode = str(penalty_daily.get("mode") or "")
    penalty_lenses = int(penalty_summary.get("lenses_evaluated") or 0)
    penalty_penalty_count = int(penalty_summary.get("recommendations_with_penalty") or 0)

    checks = {
        "promotion_gate_pass": gate_pass,
        "manual_signoff_go": go_manual,
        "manual_lock_approved": lock_approved,
        "readiness_ready": readiness_ready,
        "stage2_realset_gate_pass": realset_pass,
        "auto_bridge_disabled": auto_bridge_off,
        "auto_live_disabled": auto_live_off,
        "human_signoff_required": human_required,
        "shadow_blockers_zero": len(shadow_blockers) == 0,
    }
    failed_checks = [name for name, ok in checks.items() if not ok]
    all_green = len(failed_checks) == 0

    decision = "READY_FOR_COMMANDER_SIGNOFF" if all_green else "HOLD_NEEDS_REVIEW"
    worksheet = {
        "schema": "myeongni_manual_signoff_worksheet_v1",
        "generated_at_utc": _now_utc(),
        "decision": decision,
        "all_green": all_green,
        "checklist": checks,
        "failed_checks": failed_checks,
        "summary": {
            "promotion_gate_status": gate.get("status"),
            "promotion_decision": gate.get("decision"),
            "manual_lock_final_decision": lock_doc.get("final_decision"),
            "readiness": readiness.get("readiness"),
            "stage2_realset_count": realset_count,
            "shadow_decision": shadow_decision,
            "shadow_blockers": shadow_blockers,
            "shadow_warnings": shadow_warnings,
            "penalty_mode": penalty_mode,
            "penalty_lenses_evaluated": penalty_lenses,
            "penalty_recommendations_with_penalty": penalty_penalty_count,
        },
        "constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
        },
        "evidence_paths": {
            "promotion_gate": str(args.promotion_gate.resolve()),
            "manual_lock": str(args.manual_lock.resolve()),
            "readiness": str(args.readiness.resolve()),
            "stage2_realset_gate": str(args.stage2_realset_gate.resolve()),
            "shadow_governance": str(args.shadow_governance.resolve()),
            "penalty_daily": str(args.penalty_daily.resolve()),
        },
        "operator_action": {
            "approve_if_all_green": all_green,
            "review_items_if_hold": failed_checks,
        },
    }

    _write_json(args.out, worksheet)
    print(f"WROTE: {args.out}")
    print(f"decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
