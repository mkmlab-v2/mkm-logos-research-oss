#!/usr/bin/env python3
"""Track B — transplant Logos layered-context pattern into B2B proposal logic artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/logos_b2b_proposal_evolution_loop_spec_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_b2b_proposal_logic_artifact_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _logos_structure_pattern(distill: dict[str, Any] | None) -> dict[str, Any]:
    refs = distill.get("evidence_refs") if isinstance(distill, dict) else []
    lock = (distill or {}).get("citation_lock") if isinstance(distill, dict) else {}
    narrative = (distill or {}).get("distill_narrative_stub_ko") or {}
    return {
        "pattern_id": "LOGOS-PATTERN:layered_context_v1",
        "source_theme": (distill or {}).get("source_slice", {}).get("theme_id", "john_1_logos"),
        "layers": [
            {"slot": "field", "logos_analog": "historical-theological frame (non-exported)"},
            {"slot": "evidence_anchors", "locked_count": lock.get("locked_count", 0)},
            {"slot": "narrative", "citation_valid": narrative.get("citation_valid")},
            {"slot": "operator_posture", "b2b_analog": "SEND_GATE HOLD / human commander"},
        ],
        "evidence_anchor_count": len(refs) if isinstance(refs, list) else 0,
        "pedagogical_only": True,
        "note": "Structure transplant only — no verse text promoted to B2B sales copy",
    }


def _proposal_claims(
    b2b_spec: dict[str, Any] | None,
    hub_md: str,
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = [
        {
            "claim_id": "CLAIM-B2B-SCOPE",
            "labels": ["TRACK_B", "HYPO", "B2B_ONLY"],
            "body_ko": "[HYPO] 본 제안·허브는 동료 한의사 B2B 연수 전용이며 B2C 클리닉 퍼널·소개 목적이 아닙니다.",
            "clause_refs": ["STATIC-DISCLAIMER-01", "STATIC-DISCLAIMER-02", "BARRIER-02"],
            "barrier_ids": ["BARRIER-02"],
            "logos_structure_slot": "field",
        },
        {
            "claim_id": "CLAIM-FUNNEL-ISOLATION",
            "labels": ["TRACK_B", "HYPO"],
            "body_ko": "[HYPO] B2B 수강 데이터와 클리닉 인테이크 웹훅·환자 퍼널은 물리적으로 분리됩니다.",
            "clause_refs": ["BARRIER-01"],
            "barrier_ids": ["BARRIER-01"],
            "logos_structure_slot": "evidence_anchors",
        },
        {
            "claim_id": "CLAIM-NO-EFFICACY",
            "labels": ["TRACK_B", "HYPO", "NON_GATING"],
            "body_ko": "[HYPO] 교육 자료는 학술·실습 참고이며 치료 효능·임상 자격을 보장하지 않습니다.",
            "clause_refs": ["STATIC-DISCLAIMER-03", "BARRIER-03"],
            "barrier_ids": ["BARRIER-03"],
            "logos_structure_slot": "narrative",
        },
        {
            "claim_id": "CLAIM-SEND-HOLD",
            "labels": ["TRACK_B", "HYPO", "SEND_HOLD"],
            "body_ko": "[HYPO] 외부 송출·실발송은 send_gate HOLD 및 지휘관·법무 승인 전까지 금지됩니다.",
            "clause_refs": ["GOV-SEND-HOLD", "BARRIER-02"],
            "barrier_ids": ["BARRIER-02"],
            "logos_structure_slot": "operator_posture",
        },
        {
            "claim_id": "CLAIM-STRUCTURE-TRANSPLANT",
            "labels": ["TRACK_B", "HYPO", "PEDAGOGICAL"],
            "body_ko": (
                "[HYPO] 요한복음 1장 로고스 연구에서 확보한 '증거 앵커 필수·역추적 검증' 구조만 "
                "B2B 제안 논리 검증기에 이식합니다. 신학적 주장·구절 인용은 B2B 카피로 승격하지 않습니다."
            ),
            "clause_refs": ["LOGOS-PATTERN:layered_context_v1"],
            "barrier_ids": [],
            "logos_structure_slot": "conflict_resolver",
        },
    ]
    if b2b_spec:
        gov = b2b_spec.get("governance") or {}
        if gov.get("send_gate") is not None and gov.get("send_gate") != "HOLD":
            claims.append(
                {
                    "claim_id": "CLAIM-GOV-DRIFT",
                    "labels": ["TRACK_B", "HYPO", "DRIFT_PROBE"],
                    "body_ko": "[HYPO] governance.send_gate가 HOLD가 아님 — 검증기가 차단해야 함.",
                    "clause_refs": ["GOV-SEND-HOLD"],
                    "barrier_ids": ["BARRIER-02"],
                    "logos_structure_slot": "operator_posture",
                    "_test_only": True,
                }
            )
    if "환자 유치" in hub_md:
        claims.append(
            {
                "claim_id": "CLAIM-HUB-FORBIDDEN-DRIFT",
                "labels": ["TRACK_B", "HYPO"],
                "body_ko": "환자 유치 문구 감지 — 이 클레임은 검증 실패를 유발해야 함.",
                "clause_refs": ["ORPHAN-FORBIDDEN"],
                "barrier_ids": ["BARRIER-02"],
                "logos_structure_slot": "narrative",
                "_test_only": True,
            }
        )
    return [c for c in claims if not c.get("_test_only")]


def build(
    *,
    spec_doc: dict[str, Any],
    b2b_spec: dict[str, Any] | None,
    logos_distill: dict[str, Any] | None,
    hub_md: str,
    barrier_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    claims = _proposal_claims(b2b_spec, hub_md)
    return {
        "schema": "logos_b2b_proposal_logic_artifact_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "track_a_bridge": False,
        "b2b_target_id": spec_doc.get("inputs", {}).get("b2b_target_id", "gwangmyeong_baekje"),
        "logos_reasoning_transplant": _logos_structure_pattern(logos_distill),
        "proposal_claims": claims,
        "inputs_snapshot": {
            "barrier_audit_ok": (barrier_audit or {}).get("ok"),
            "barrier_audit_status": (barrier_audit or {}).get("audit_status"),
            "logos_citation_locked": ((logos_distill or {}).get("citation_lock") or {}).get("locked_count"),
            "static_hub_chars": len(hub_md),
        },
        "reproduce": "py scripts/build_logos_b2b_proposal_logic_artifact_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    loop_spec = _load(args.spec)
    if not loop_spec:
        raise SystemExit(f"missing loop spec: {args.spec}")

    inputs = loop_spec.get("inputs") or {}
    logos_path = ROOT / str(inputs.get("logos_distill_citation_lock", "")).replace("\\", "/")
    b2b_spec_path = ROOT / str(inputs.get("b2b_spec", "")).replace("\\", "/")
    barrier_path = ROOT / str(inputs.get("b2b_barrier_audit", "")).replace("\\", "/")
    hub_path = ROOT / str(inputs.get("b2b_static_hub", "")).replace("\\", "/")

    logos_distill = _load(logos_path)
    b2b_spec = _load(b2b_spec_path)
    barrier_audit = _load(barrier_path)
    hub_md = hub_path.read_text(encoding="utf-8") if hub_path.is_file() else ""

    doc = build(
        spec_doc=loop_spec,
        b2b_spec=b2b_spec,
        logos_distill=logos_distill,
        hub_md=hub_md,
        barrier_audit=barrier_audit,
    )
    doc["inputs_snapshot"]["b2b_spec_present"] = b2b_spec is not None

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.relative_to(ROOT)).replace("\\", "/"),
                "claims": len(doc["proposal_claims"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
