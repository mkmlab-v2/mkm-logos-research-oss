# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.9, K:0.4, M:0.6}
# Balance: 94
# Purpose: Build thin self-critique artifact from unified state snapshot.
# Keywords: self_critique, counterfactual, unified_state, advisory
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "unified_state_snapshot_v1_latest.json"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "unified_self_critique_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(snapshot: dict[str, Any]) -> dict[str, Any]:
    nodes = snapshot.get("state_nodes") or {}
    summary = snapshot.get("summary") or {}
    checklist = nodes.get("a_track_checklist") or {}
    go_nogo = nodes.get("a_track_go_nogo") or {}
    health = nodes.get("automation_health") or {}

    pending = checklist.get("reasons") or []
    failed = go_nogo.get("reasons") or []

    if pending:
        primary_decision = "HOLD_STAGE"
        counterfactual = "PROMOTE_TO_S2_NOW"
        why_not = "필수 체크리스트 미완료 항목 존재"
        risk_delta = "HIGHER_DRAWDOWN_AND_POLICY_BREACH_RISK"
    elif health.get("readiness") != "READY":
        primary_decision = "HOLD_STAGE"
        counterfactual = "KEEP_PROMOTION_PIPELINE_ACTIVE"
        why_not = "운영 헬스 readiness 미충족"
        risk_delta = "HIGHER_RUNTIME_FAILURE_RISK"
    else:
        primary_decision = "MAINTAIN_CURRENT_STAGE"
        counterfactual = "MANUAL_REVIEW_FOR_NEXT_STAGE"
        why_not = "자동 승급 금지 정책(권고 전용 루프)"
        risk_delta = "LOW_BUT_NONZERO_GOVERNANCE_RISK"

    recommendations = []
    if "s3-01" in pending:
        recommendations.append("주간 S3 증거 누적(weeks_collected) 자동 러너 지속 실행")
    if "price_output_locked_true" in failed:
        recommendations.append("price_output_unlock 조건 충족 전 잠금 해제 금지")
    if "high_reliability_decision_is_hold" in failed:
        recommendations.append("high_reliability HOLD 해제 연속성(2사이클) 확인")
    if not recommendations:
        recommendations.append("현재 단계 유지, 다음 승급은 수동 리뷰 후 결정")

    return {
        "schema": "unified_self_critique_v1",
        "schema_version": 1,
        "generated_at_utc": _now_utc(),
        "mode": "advisory_only",
        "auto_apply": False,
        "input_snapshot": "docs/final/artifacts/unified_state_snapshot_v1_latest.json",
        "assessment": {
            "decision": primary_decision,
            "current_stage": summary.get("stage"),
            "readiness": summary.get("readiness"),
            "status": summary.get("status"),
        },
        "counterfactual_review": {
            "best_alternative": counterfactual,
            "why_not_chosen": why_not,
            "expected_risk_delta": risk_delta,
        },
        "recommendations": recommendations,
        "evidence": {
            "checklist_pending": pending,
            "go_nogo_failed_reasons": failed,
            "automation_health_reasons": health.get("reasons") or [],
        },
        "notes_ko": [
            "본 루프는 권고 전용이며 자동 승급/자동 반영을 수행하지 않는다.",
            "반사실 평가는 게이트 우회가 아니라 리스크 비교 목적이다.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build unified self-critique advisory artifact.")
    ap.add_argument("--snapshot", type=Path, default=SNAPSHOT_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    snapshot = _load(args.snapshot if args.snapshot.is_absolute() else ROOT / args.snapshot)
    payload = build(snapshot=snapshot)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"decision={payload['assessment']['decision']}")
    print(f"best_alternative={payload['counterfactual_review']['best_alternative']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
