#!/usr/bin/env python3
"""Build weekly A-track Go/No-Go status JSON from latest artifacts.

Conservative defaults:
- Strict AND gate for stage readiness
- Any system error defaults to NO_GO (configurable)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json"
ATRACK_CLI_DECISION_PATH = ROOT / "reports" / "a_track_promotion_decision_latest.json"
MULTIWEEK_TRACKER_PATH = ROOT / "docs" / "final" / "artifacts" / "a_track_multiweek_stability_tracker_v1_latest.json"
OPERATOR_APPROVAL_PROTOCOL_PATH = ROOT / "docs" / "final" / "artifacts" / "a_track_operator_approval_protocol_v1_latest.json"
POLICY_FLOOR_GOV_PATH = ROOT / "docs" / "final" / "artifacts" / "a_track_policy_floor_governance_decision_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _bool(val: Any) -> bool:
    return bool(val)


def _add_check(
    checks: Dict[str, bool],
    reasons: List[str],
    key: str,
    ok: bool,
    fail_reason: str,
) -> None:
    checks[key] = ok
    if not ok:
        reasons.append(fail_reason)


def _strict_and(checks: Dict[str, bool]) -> bool:
    return all(checks.values()) if checks else False


def _optional_json(path: Path) -> Tuple[Dict[str, Any], bool]:
    if not path.is_file():
        return {}, False
    try:
        return _read_json(path), True
    except Exception:
        return {}, False


def _read_atrack_cli_decision(path: Path) -> Dict[str, Any]:
    """Optional human CLI receipt from approve_intervention_promotion.ps1 (-Target a_track)."""
    if not path.is_file():
        return {
            "present": False,
            "path": str(path),
            "action": None,
            "status": None,
            "requested_stage": None,
            "accepted_for_stage": None,
        }
    try:
        raw = _read_json(path)
    except Exception:
        return {
            "present": True,
            "path": str(path),
            "parse_error": True,
            "action": None,
            "status": None,
            "requested_stage": None,
            "accepted_for_stage": None,
        }
    action = str(raw.get("action") or "")
    status = str(raw.get("status") or "")
    stage = str(raw.get("requested_stage") or "")
    accepted = action == "approve" and status == "accepted"
    allowed = {"S2_PAPER_STRICT", "S3_PAPER_SCALED", "S4_LIMITED_LIVE"}
    accepted_for = stage if accepted and stage in allowed else None
    return {
        "present": True,
        "path": str(path),
        "schema": raw.get("schema"),
        "action": action or None,
        "status": status or None,
        "requested_stage": stage or None,
        "accepted_for_stage": accepted_for,
        "generated_at": raw.get("generated_at"),
        "approver": raw.get("approver"),
    }


def _cli_ok(cli: Dict[str, Any], stage: str) -> bool:
    return cli.get("accepted_for_stage") == stage


def evaluate(
    *,
    on_system_error: str,
) -> Dict[str, Any]:
    inputs = {
        "high_reliability_mode_gate": ROOT / "docs" / "final" / "artifacts" / "high_reliability_mode_gate_latest.json",
        "trinity_track_quality": ROOT / "docs" / "final" / "artifacts" / "trinity_track_quality_report_latest.json",
        "prophecy_monthly": ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json",
        "chronos_holdout_2026": ROOT / "data" / "chronos_forward_training" / "holdout_2026_result.json",
        "a_track_price_output_unlock_policy": ROOT / "docs" / "final" / "artifacts" / "a_track_price_output_unlock_policy_v1_latest.json",
        "a_track_high_reliability_release_plan": ROOT / "docs" / "final" / "artifacts" / "a_track_high_reliability_release_plan_v1_latest.json",
    }
    optional_inputs = {
        "a_track_hold_release_checklist": ROOT
        / "docs"
        / "final"
        / "artifacts"
        / "a_track_hold_release_checklist_v1_latest.json",
    }

    errors: List[str] = []
    docs: Dict[str, Dict[str, Any]] = {}
    for name, path in inputs.items():
        if not path.is_file():
            errors.append(f"missing_file:{name}:{path}")
            continue
        try:
            docs[name] = _read_json(path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"json_read_error:{name}:{path}:{exc}")

    for name, path in optional_inputs.items():
        if not path.is_file():
            docs[name] = {"checklist": []}
            continue
        try:
            docs[name] = _read_json(path)
        except Exception as exc:  # pragma: no cover
            errors.append(f"json_read_error:{name}:{path}:{exc}")

    meta: Dict[str, Any] = {
        "generated_at_utc": _utc_now(),
        "system_error_policy": on_system_error,
        "input_paths": {k: str(v) for k, v in inputs.items()}
        | {k: str(v) for k, v in optional_inputs.items()},
        "optional_input_paths": {
            "a_track_promotion_cli": str(ATRACK_CLI_DECISION_PATH),
            "a_track_multiweek_stability_tracker": str(MULTIWEEK_TRACKER_PATH),
            "a_track_operator_approval_protocol": str(OPERATOR_APPROVAL_PROTOCOL_PATH),
            "a_track_policy_floor_governance_decision": str(POLICY_FLOOR_GOV_PATH),
        },
        "input_errors": errors,
    }

    if errors:
        if on_system_error == "no_go":
            return {
                "schema": "a_track_go_nogo_status_v1",
                "meta": meta,
                "result": {
                    "overall_go_no_go": "NO_GO",
                    "recommended_stage": "S0_LOCKED",
                    "failed_reasons": errors + ["system_error_fail_safe_no_go"],
                },
                "stage_readiness": {
                    "s1_shadow_ready": False,
                    "s2_paper_strict_ready": False,
                    "s3_paper_scaled_ready": False,
                    "s4_limited_live_ready": False,
                },
                "checks": {},
            }
        return {
            "schema": "a_track_go_nogo_status_v1",
            "meta": meta,
            "result": {
                "overall_go_no_go": "HOLD",
                "recommended_stage": "S1_SHADOW",
                "failed_reasons": errors + ["system_error_hold_previous_stage"],
            },
            "stage_readiness": {
                "s1_shadow_ready": True,
                "s2_paper_strict_ready": False,
                "s3_paper_scaled_ready": False,
                "s4_limited_live_ready": False,
            },
            "checks": {},
        }

    high_rel = docs["high_reliability_mode_gate"]
    trinity = docs["trinity_track_quality"]
    prophecy = docs["prophecy_monthly"]
    holdout = docs["chronos_holdout_2026"]
    checklist = docs["a_track_hold_release_checklist"]
    unlock_policy = docs["a_track_price_output_unlock_policy"]
    hr_release_plan = docs["a_track_high_reliability_release_plan"]
    cli = _read_atrack_cli_decision(ATRACK_CLI_DECISION_PATH)

    tracker_doc, tracker_present = _optional_json(MULTIWEEK_TRACKER_PATH)
    approval_doc, approval_present = _optional_json(OPERATOR_APPROVAL_PROTOCOL_PATH)
    policy_gov_doc, policy_gov_present = _optional_json(POLICY_FLOOR_GOV_PATH)

    checklist_items = checklist.get("checklist") or []
    done_by_id = {
        str(item.get("id")): bool(item.get("done"))
        for item in checklist_items
        if isinstance(item, dict)
    }

    multiweek_ready = bool((tracker_doc.get("summary") or {}).get("ready_for_s3_gate"))
    approval_status_u = str(approval_doc.get("status") or "").upper()
    approval_protocol_defined = approval_status_u in {"READY_FOR_SIGNOFF", "APPROVED", "ACTIVE"}
    policy_gov_status_u = str(policy_gov_doc.get("status") or "").upper()
    policy_gov_defined = policy_gov_status_u in {"APPROVED", "ACTIVE"}

    checks: Dict[str, bool] = {}
    failed_reasons: List[str] = []

    _add_check(
        checks,
        failed_reasons,
        "high_reliability_mode_gate_pass",
        high_rel.get("decision") == "PASS",
        "high_reliability_mode_gate_not_pass",
    )
    _add_check(
        checks,
        failed_reasons,
        "trinity_overall_pass",
        (trinity.get("summary") or {}).get("overall_decision") == "PASS",
        "trinity_overall_not_pass",
    )

    s1_ready = _strict_and(
        {
            "high_reliability_mode_gate_pass": checks["high_reliability_mode_gate_pass"],
            "trinity_overall_pass": checks["trinity_overall_pass"],
        }
    )

    high_rel_decision = (prophecy.get("meta") or {}).get("high_reliability_decision")
    price_output_locked = _bool((prophecy.get("meta") or {}).get("price_output_locked"))
    unlock_policy_status = str(unlock_policy.get("status") or "").upper()
    hr_release_status = str(hr_release_plan.get("status") or "").upper()
    unlock_policy_defined = unlock_policy_status in {"READY_FOR_SIGNOFF", "APPROVED", "ACTIVE"}
    hr_release_defined = hr_release_status in {"READY_FOR_SIGNOFF", "APPROVED", "ACTIVE"}
    effective_high_rel_not_hold = (
        (high_rel_decision != "HOLD") or hr_release_defined or bool(done_by_id.get("hrm-01"))
    )
    effective_price_unlocked = (price_output_locked is False) or unlock_policy_defined or bool(
        done_by_id.get("lock-01")
    )
    holdout_direction = float(holdout.get("direction_match_rate") or 0.0)

    _add_check(
        checks,
        failed_reasons,
        "high_reliability_decision_not_hold",
        effective_high_rel_not_hold,
        "high_reliability_decision_is_hold",
    )
    _add_check(
        checks,
        failed_reasons,
        "price_output_unlocked",
        effective_price_unlocked,
        "price_output_locked_true",
    )
    _add_check(
        checks,
        failed_reasons,
        "chronos_holdout_direction_match_gte_50",
        holdout_direction >= 50.0,
        f"chronos_holdout_direction_match_below_threshold:{holdout_direction:.4f}",
    )

    policy_gate_ok = policy_gov_defined or bool(done_by_id.get("policy-01", False))
    _add_check(
        checks,
        failed_reasons,
        "policy_floor_governance_ok",
        policy_gate_ok,
        "policy_floor_governance_incomplete",
    )

    cli_s2 = _cli_ok(cli, "S2_PAPER_STRICT")
    cli_s3 = _cli_ok(cli, "S3_PAPER_SCALED")
    cli_s4 = _cli_ok(cli, "S4_LIMITED_LIVE")
    checks["a_track_human_cli_s2_accepted"] = cli_s2
    checks["a_track_human_cli_s3_accepted"] = cli_s3
    checks["a_track_human_cli_s4_accepted"] = cli_s4
    _add_check(
        checks,
        failed_reasons,
        "a_track_human_cli_s2_accepted",
        cli_s2,
        "a_track_human_cli_missing_or_not_accepted_for_s2",
    )

    s3_evidence_ready = bool(done_by_id.get("s3-01", False)) or multiweek_ready
    s4_operator_ready = bool(done_by_id.get("s4-01", False)) or approval_protocol_defined
    _add_check(
        checks,
        failed_reasons,
        "s3_multiweek_evidence_ready",
        s3_evidence_ready,
        "s3_requires_multiweek_stability_evidence",
    )
    _add_check(
        checks,
        failed_reasons,
        "s4_operator_checklist_ready",
        s4_operator_ready,
        "s4_operator_checklist_incomplete",
    )

    s2_tech_ready = _strict_and(
        {
            "s1_ready": s1_ready,
            "high_reliability_decision_not_hold": checks["high_reliability_decision_not_hold"],
            "price_output_unlocked": checks["price_output_unlocked"],
            "chronos_holdout_direction_match_gte_50": checks["chronos_holdout_direction_match_gte_50"],
            "policy_floor_governance_ok": checks["policy_floor_governance_ok"],
        }
    )

    s2_ready = s2_tech_ready and cli_s2
    s3_ready = s3_evidence_ready and cli_s3
    s4_ready = s4_operator_ready and cli_s4

    if s2_ready:
        overall = "GO"
        recommended_stage = "S2_PAPER_STRICT"
    elif s1_ready:
        overall = "HOLD"
        recommended_stage = "S1_SHADOW"
    else:
        overall = "NO_GO"
        recommended_stage = "S0_LOCKED"

    return {
        "schema": "a_track_go_nogo_status_v1",
        "meta": meta,
        "snapshot": {
            "high_reliability_mode_gate_decision": high_rel.get("decision"),
            "trinity_overall_decision": (trinity.get("summary") or {}).get("overall_decision"),
            "high_reliability_decision": high_rel_decision,
            "price_output_locked": price_output_locked,
            "high_reliability_release_plan_status": hr_release_status,
            "price_unlock_policy_status": unlock_policy_status,
            "chronos_holdout_direction_match_rate": holdout_direction,
            "a_track_promotion_cli": cli,
            "multiweek_stability_tracker_present": tracker_present,
            "multiweek_stability_ready_for_s3_gate": multiweek_ready,
            "operator_approval_protocol_present": approval_present,
            "operator_approval_protocol_status": approval_status_u or None,
            "policy_floor_governance_present": policy_gov_present,
            "policy_floor_governance_status": policy_gov_status_u or None,
            "hold_release_checklist_derived": {
                "done_lock_01": bool(done_by_id.get("lock-01")),
                "done_s3_01": bool(done_by_id.get("s3-01")),
                "done_s4_01": bool(done_by_id.get("s4-01")),
                "done_hrm_01": bool(done_by_id.get("hrm-01")),
                "done_policy_01": bool(done_by_id.get("policy-01")),
            },
        },
        "checks": checks,
        "stage_readiness": {
            "s1_shadow_ready": s1_ready,
            "s2_paper_strict_ready": s2_ready,
            "s3_paper_scaled_ready": s3_ready,
            "s4_limited_live_ready": s4_ready,
        },
        "result": {
            "overall_go_no_go": overall,
            "recommended_stage": recommended_stage,
            "failed_reasons": failed_reasons,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build A-track weekly Go/No-Go status JSON.")
    ap.add_argument(
        "--on-system-error",
        choices=("no_go", "hold_s1"),
        default="no_go",
        help="How to handle missing/corrupted inputs.",
    )
    ap.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output JSON path.",
    )
    args = ap.parse_args()

    payload = evaluate(on_system_error=args.on_system_error)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"overall_go_no_go: {payload.get('result', {}).get('overall_go_no_go')}")
    print(f"recommended_stage: {payload.get('result', {}).get('recommended_stage')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
