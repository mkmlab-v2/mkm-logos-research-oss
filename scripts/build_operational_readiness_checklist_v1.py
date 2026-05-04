from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _exists(path: Path) -> bool:
    return path.exists() and path.is_file()


def _check(
    *,
    condition_id: str,
    description: str,
    required: bool,
    check_type: str,
    evidence_path: str,
    expected: Any,
    actual: Any,
    status: str,
) -> Dict[str, Any]:
    return {
        "id": condition_id,
        "description": description,
        "required": required,
        "check_type": check_type,
        "evidence_path": evidence_path,
        "expected": expected,
        "actual": actual,
        "status": status,
        "last_checked_utc": _utc_now(),
    }


def build_payload(root: Path, mission_id: str) -> Dict[str, Any]:
    artifacts_dir = root / "docs" / "final" / "artifacts"
    reports_dir = root / "reports"

    p0_script = root / "scripts" / "verify_p0_constitution_gate_paths.ps1"
    a_track_status_path = artifacts_dir / "a_track_go_nogo_status_latest.json"
    b_track_gate_path = artifacts_dir / "trackb_weekly_gate_recheck_latest.json"
    human_approval_path = reports_dir / "trading_human_execution_approval_latest.json"
    decisions_log_path = reports_dir / "agent_decisions_log.jsonl"

    a_track_status = _read_json(a_track_status_path)
    b_track_gate = _read_json(b_track_gate_path)
    human_approval = _read_json(human_approval_path)

    a_track_result = a_track_status.get("result", {})
    a_track_overall = str(a_track_result.get("overall_go_no_go", ""))
    b_track_decision = str(b_track_gate.get("decision", ""))
    human_approved = bool(human_approval.get("approved", False))

    done_conditions: List[Dict[str, Any]] = []
    done_conditions.append(
        _check(
            condition_id="dc-001",
            description="P0 constitution gate verifier script is present",
            required=True,
            check_type="artifact_exists",
            evidence_path="scripts/verify_p0_constitution_gate_paths.ps1",
            expected=True,
            actual=_exists(p0_script),
            status="PASS" if _exists(p0_script) else "FAIL",
        )
    )
    done_conditions.append(
        _check(
            condition_id="dc-002",
            description="A-track go/no-go status artifact exists",
            required=True,
            check_type="artifact_exists",
            evidence_path="docs/final/artifacts/a_track_go_nogo_status_latest.json",
            expected=True,
            actual=_exists(a_track_status_path),
            status="PASS" if _exists(a_track_status_path) else "FAIL",
        )
    )
    done_conditions.append(
        _check(
            condition_id="dc-003",
            description="A-track go/no-go is not empty",
            required=True,
            check_type="artifact_value",
            evidence_path="docs/final/artifacts/a_track_go_nogo_status_latest.json",
            expected="GO|HOLD",
            actual=a_track_overall if a_track_overall else None,
            status="PASS" if a_track_overall in {"GO", "HOLD"} else "FAIL",
        )
    )
    done_conditions.append(
        _check(
            condition_id="dc-004",
            description="B-track decision remains research-lane only",
            required=True,
            check_type="artifact_value",
            evidence_path="docs/final/artifacts/trackb_weekly_gate_recheck_latest.json",
            expected="GO_RESEARCH|HOLD",
            actual=b_track_decision if b_track_decision else None,
            status="PASS" if b_track_decision in {"GO_RESEARCH", "HOLD"} else "FAIL",
        )
    )
    done_conditions.append(
        _check(
            condition_id="dc-005",
            description="Human approval evidence exists and is approved for live promotion",
            required=True,
            check_type="manual_approval",
            evidence_path="reports/trading_human_execution_approval_latest.json",
            expected=True,
            actual=human_approved,
            status="PASS" if human_approved else "FAIL",
        )
    )

    required_checks = [c for c in done_conditions if c.get("required")]
    failed_ids = [c["id"] for c in required_checks if c.get("status") != "PASS"]
    passed_total = sum(1 for c in required_checks if c.get("status") == "PASS")
    all_required_passed = len(failed_ids) == 0

    fact_lock_pass = _exists(a_track_status_path) and _exists(b_track_gate_path)
    btrack_atrack_wall_pass = b_track_decision in {"GO_RESEARCH", "HOLD"}
    human_approval_required = True
    human_approval_received = human_approved
    live_promotion_allowed = all_required_passed and fact_lock_pass and btrack_atrack_wall_pass and human_approved

    judge_decision = "GO_CONTROLLED" if live_promotion_allowed else "HOLD"
    next_action = (
        "Proceed with controlled promotion sequence and keep runtime monitoring active"
        if live_promotion_allowed
        else "Keep HOLD. Resolve failed done-conditions and rerun this builder"
    )

    runtime_state = "GO" if live_promotion_allowed else ("WAITING_APPROVAL" if not human_approved else "HOLD")
    last_error = None if live_promotion_allowed else ("waiting_for_human_approval" if not human_approved else "hard_gate_unmet")

    return {
        "schema": "operational_readiness_checklist_v1",
        "generated_at_utc": _utc_now(),
        "mission_id": mission_id,
        "scope": {
            "track": "A-track",
            "environment": "controlled_shadow",
            "owner_mode": "solo",
        },
        "done_conditions": done_conditions,
        "hard_gates": {
            "fact_lock_pass": fact_lock_pass,
            "btrack_atrack_wall_pass": btrack_atrack_wall_pass,
            "human_approval_required": human_approval_required,
            "human_approval_received": human_approval_received,
            "live_promotion_allowed": live_promotion_allowed,
        },
        "runtime_state": {
            "state": runtime_state,
            "retry_count": 0,
            "max_retries": 3,
            "last_error": last_error,
        },
        "verification": {
            "required_total": len(required_checks),
            "passed_total": passed_total,
            "failed_ids": failed_ids,
            "all_required_passed": all_required_passed,
            "judge_decision": judge_decision,
            "next_action": next_action,
        },
        "artifacts": {
            "plan_path": "MISSION_LOG.md",
            "session_log_path": "reports/agent_decisions_log.jsonl" if _exists(decisions_log_path) else "reports/agent_decisions_log.jsonl (missing)",
            "progress_log_path": "docs/final/artifacts/a_track_go_nogo_slack_delivery_log.jsonl",
            "checklist_path": "docs/final/artifacts/operational_readiness_checklist_v1_latest.json",
        },
        "context_reset_contract": {
            "handoff_file_path": "docs/final/CURRENT_OPS_SNAPSHOT.md",
            "compaction_version": "v1",
            "preserve_fields": [
                "mission_id",
                "scope",
                "done_conditions",
                "hard_gates",
                "verification.judge_decision",
                "verification.next_action",
            ],
        },
        "memory_drift_audit": {
            "enabled": True,
            "last_audit_utc": None,
            "drift_flags": [],
            "resolution_status": "REVIEW_REQUIRED",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build operational readiness checklist latest artifact.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument("--mission-id", default="ops-readiness-bootstrap-v1")
    ap.add_argument(
        "--out",
        default="docs/final/artifacts/operational_readiness_checklist_v1_latest.json",
    )
    args = ap.parse_args()

    root = Path(args.workspace_root).resolve()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = root / out_path

    payload = build_payload(root=root, mission_id=str(args.mission_id))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"judge_decision: {payload['verification']['judge_decision']}")
    print(f"failed_ids: {payload['verification']['failed_ids']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
