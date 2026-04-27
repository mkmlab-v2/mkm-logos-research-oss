# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.3, M:0.6}
# Balance: 94
# Purpose: Build actionable checklist to release A-track HOLD safely.
# Keywords: track_a, hold, checklist, gate, governance
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GO_NOGO_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_go_nogo_status_latest.json"
POLICY_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_decision_v1.json"
UNLOCK_POLICY_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_price_output_unlock_policy_v1_latest.json"
APPROVAL_PROTOCOL_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_operator_approval_protocol_v1_latest.json"
HR_RELEASE_PLAN_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_high_reliability_release_plan_v1_latest.json"
POLICY_GOV_DECISION_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_policy_floor_governance_decision_v1_latest.json"
MULTIWEEK_TRACKER_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_multiweek_stability_tracker_v1_latest.json"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "a_track_hold_release_checklist_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _task(task_id: str, title: str, gate: str, action: str, done: bool = False) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "gate": gate,
        "required": True,
        "done": done,
        "action": action,
    }


def build_checklist(
    go_nogo: dict[str, Any],
    policy: dict[str, Any],
    unlock_policy: dict[str, Any],
    approval_protocol: dict[str, Any],
    hr_release_plan: dict[str, Any],
    policy_governance_decision: dict[str, Any],
    multiweek_tracker: dict[str, Any],
) -> dict[str, Any]:
    result = (go_nogo.get("result") or {})
    stage = str(result.get("recommended_stage") or "")
    overall = str(result.get("overall_go_no_go") or "")
    failed = set(result.get("failed_reasons") or [])
    policy_decision = str(policy.get("decision") or "")
    unlock_status = str(unlock_policy.get("status") or "").upper()
    unlock_policy_defined = unlock_status in {"READY_FOR_SIGNOFF", "APPROVED", "ACTIVE"}
    approval_status = str(approval_protocol.get("status") or "").upper()
    approval_protocol_defined = approval_status in {"READY_FOR_SIGNOFF", "APPROVED", "ACTIVE"}
    hr_plan_status = str(hr_release_plan.get("status") or "").upper()
    hr_release_defined = hr_plan_status in {"READY_FOR_SIGNOFF", "APPROVED", "ACTIVE"}
    policy_gov_status = str(policy_governance_decision.get("status") or "").upper()
    policy_gov_defined = policy_gov_status in {"APPROVED", "ACTIVE"}
    multiweek_ready = bool((multiweek_tracker.get("summary") or {}).get("ready_for_s3_gate"))

    tasks: list[dict[str, Any]] = []
    tasks.append(
        _task(
            "lock-01",
            "가격 출력 잠금 해제 조건 확정",
            "price_output_locked_true",
            "price output unlock policy를 수치 기준(최소 기간/최대 DD/재잠금 트리거)으로 확정하고 아티팩트로 기록",
            done=unlock_policy_defined,
        )
    )
    tasks.append(
        _task(
            "s3-01",
            "다주간 안정성 증거 누적",
            "s3_requires_multiweek_stability_evidence",
            "주간 시계열 증거(수익분포, 변동성, 최악구간, 비용 반영 성과)를 연속 주차 기준으로 누적",
            done=multiweek_ready,
        )
    )
    tasks.append(
        _task(
            "s4-01",
            "운영자 명시 승인 프로토콜 실행",
            "s4_requires_operator_explicit_approval",
            "S2->S3, S3->S4 승급 승인자/근거 파일/롤백 트리거를 확정하고 승인 이벤트를 남김",
            done=approval_protocol_defined,
        )
    )
    tasks.append(
        _task(
            "hrm-01",
            "고신뢰 모드 HOLD 해제 조건 충족",
            "high_reliability_decision_is_hold",
            "high reliability decision을 HOLD에서 해제할 수 있도록 입력 품질과 보수적 임계치를 재검증",
            done=hr_release_defined,
        )
    )
    tasks.append(
        _task(
            "policy-01",
            "정책 바닥선(0.49) 거버넌스 결정 유지/변경",
            "policy_floor_governance",
            "현재 policy floor 유지 또는 변경을 거버넌스 아티팩트로 명시하고 Track A 주장과 일치시킴",
            done=policy_gov_defined,
        )
    )

    all_done = all(t.get("done") for t in tasks)
    if all_done:
        next_stage = "S2_PAPER_STRICT"
        next_action = "S2 paper-strict 진입 및 동일 게이트 재검증"
    else:
        next_stage = stage or "S1_SHADOW"
        next_action = "HOLD 유지. 체크리스트 미완료 항목부터 순차 해제"

    return {
        "schema": "a_track_hold_release_checklist_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "go_nogo_status": str(GO_NOGO_DEFAULT),
            "policy_floor_decision": str(POLICY_DEFAULT),
            "price_output_unlock_policy": str(UNLOCK_POLICY_DEFAULT),
            "operator_approval_protocol": str(APPROVAL_PROTOCOL_DEFAULT),
            "high_reliability_release_plan": str(HR_RELEASE_PLAN_DEFAULT),
            "policy_floor_governance_decision": str(POLICY_GOV_DECISION_DEFAULT),
            "multiweek_stability_tracker": str(MULTIWEEK_TRACKER_DEFAULT),
        },
        "current_status": {
            "overall_go_no_go": overall,
            "recommended_stage": stage,
            "failed_reasons": sorted(failed),
            "policy_floor_decision": policy_decision,
            "price_output_unlock_policy_status": unlock_status or "MISSING",
            "operator_approval_protocol_status": approval_status or "MISSING",
            "high_reliability_release_plan_status": hr_plan_status or "MISSING",
            "policy_floor_governance_status": policy_gov_status or "MISSING",
            "multiweek_stability_ready_for_s3_gate": multiweek_ready,
        },
        "checklist": tasks,
        "summary": {
            "required_total": len(tasks),
            "completed_total": sum(1 for t in tasks if t.get("done")),
            "all_required_completed": all_done,
            "next_stage_when_completed": "S2_PAPER_STRICT",
            "current_next_stage": next_stage,
            "next_action": next_action,
        },
        "notes_ko": [
            "B-track 승격 완료와 A-track 승격은 분리된 게이트로 관리한다.",
            "강제 우회 대신 증거 기반 해제를 기본 원칙으로 유지한다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build A-track HOLD release checklist artifact.")
    ap.add_argument("--go-nogo", type=Path, default=GO_NOGO_DEFAULT)
    ap.add_argument("--policy", type=Path, default=POLICY_DEFAULT)
    ap.add_argument("--unlock-policy", type=Path, default=UNLOCK_POLICY_DEFAULT)
    ap.add_argument("--approval-protocol", type=Path, default=APPROVAL_PROTOCOL_DEFAULT)
    ap.add_argument("--hr-release-plan", type=Path, default=HR_RELEASE_PLAN_DEFAULT)
    ap.add_argument("--policy-governance-decision", type=Path, default=POLICY_GOV_DECISION_DEFAULT)
    ap.add_argument("--multiweek-tracker", type=Path, default=MULTIWEEK_TRACKER_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    go_nogo_path = args.go_nogo if args.go_nogo.is_absolute() else ROOT / args.go_nogo
    policy_path = args.policy if args.policy.is_absolute() else ROOT / args.policy
    unlock_policy_path = args.unlock_policy if args.unlock_policy.is_absolute() else ROOT / args.unlock_policy
    approval_protocol_path = args.approval_protocol if args.approval_protocol.is_absolute() else ROOT / args.approval_protocol
    hr_release_plan_path = args.hr_release_plan if args.hr_release_plan.is_absolute() else ROOT / args.hr_release_plan
    policy_gov_decision_path = (
        args.policy_governance_decision
        if args.policy_governance_decision.is_absolute()
        else ROOT / args.policy_governance_decision
    )
    multiweek_tracker_path = args.multiweek_tracker if args.multiweek_tracker.is_absolute() else ROOT / args.multiweek_tracker
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    go_nogo = _load_json(go_nogo_path)
    policy = _load_json(policy_path)
    unlock_policy = _load_json(unlock_policy_path) if unlock_policy_path.is_file() else {}
    approval_protocol = _load_json(approval_protocol_path) if approval_protocol_path.is_file() else {}
    hr_release_plan = _load_json(hr_release_plan_path) if hr_release_plan_path.is_file() else {}
    policy_gov_decision = _load_json(policy_gov_decision_path) if policy_gov_decision_path.is_file() else {}
    multiweek_tracker = _load_json(multiweek_tracker_path) if multiweek_tracker_path.is_file() else {}
    payload = build_checklist(
        go_nogo=go_nogo,
        policy=policy,
        unlock_policy=unlock_policy,
        approval_protocol=approval_protocol,
        hr_release_plan=hr_release_plan,
        policy_governance_decision=policy_gov_decision,
        multiweek_tracker=multiweek_tracker,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"all_required_completed: {payload['summary']['all_required_completed']}")
    print(f"next_action: {payload['summary']['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
