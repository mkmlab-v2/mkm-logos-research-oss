#!/usr/bin/env python3
"""RQ-031: A-code promotion RQ discussion readiness ([HYPO] · operator-assist lane only)."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DRAFT = ROOT / "experiments/a_code_12ai_v2/specs/a_code_promotion_rq_draft_v1.json"
DEFAULT_READINESS = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"
DEFAULT_EVIDENCE = ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json"
DEFAULT_GATE = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/a_code_promotion_rq_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _import_ack_validator():
    path = ROOT / "scripts/validate_commander_a_code_promotion_rq_ack_v1.py"
    spec = importlib.util.spec_from_file_location("validate_promotion_rq_ack", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_ack_resolver():
    path = ROOT / "scripts/a_code_promotion_rq_ack_resolve_v1.py"
    spec = importlib.util.spec_from_file_location("a_code_promotion_rq_ack_resolve", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_readiness(
    *,
    draft: dict[str, Any],
    checklist: dict[str, Any],
    evidence: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    ack_resolver = _import_ack_resolver()
    ack_validator = _import_ack_validator()
    ack_path, ack_source = ack_resolver.resolve_promotion_rq_ack_path(None)
    if ack_path is None:
        ack_info: dict[str, Any] = {
            "present": False,
            "ok": True,
            "acknowledged": False,
            "source": ack_source,
            "promotion_rq_ack_status": "ABSENT",
        }
    else:
        ack_doc = _read(ack_path)
        ack_errors = ack_validator.validate_ack_doc(ack_doc)
        ack_info = {
            "present": True,
            "source": ack_source,
            "ack_path": str(ack_path.relative_to(ROOT)).replace("\\", "/"),
            **ack_validator.ack_summary(ack_doc, errors=ack_errors),
        }

    checklist_summary = checklist.get("summary") or {}
    gate_summary = gate.get("summary") or {}
    signoff = checklist.get("signoff") or {}

    auto_checks = {
        "draft_spec_present": draft.get("schema") == "a_code_promotion_rq_draft_v1",
        "promotion_discussion_eligible": checklist_summary.get("promotion_discussion_eligible") is True,
        "mechanical_ready": checklist_summary.get("mechanical_ready") is True,
        "human_signoff_approved": signoff.get("human_signoff_status") == "APPROVED",
        "gate_watch_continue": gate_summary.get("decision") == "WATCH_CONTINUE",
        "evidence_status_watch": evidence.get("status") == "WATCH",
    }
    auto_ok = all(auto_checks.values())

    promotion_rq_acknowledged = ack_info.get("acknowledged") is True
    discussion_ready = auto_ok and checklist_summary.get("promotion_discussion_eligible") is True
    operator_lane_ready = discussion_ready and promotion_rq_acknowledged

    blockers: list[str] = []
    if not auto_checks["promotion_discussion_eligible"]:
        blockers.append("RQ-029 promotion_discussion_eligible=false")
    if not promotion_rq_acknowledged:
        blockers.append("RQ-031 commander scope ack missing or not acknowledged")
    if evidence.get("status") != "WATCH":
        blockers.append(f"evidence status={evidence.get('status')} (expected WATCH)")

    return {
        "schema": "a_code_promotion_rq_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_id": draft.get("rq_id") or "RQ-031",
        "parent_rq": draft.get("parent_rq") or ["RQ-028", "RQ-029"],
        "hypothesis_tier": "B",
        "research_only": True,
        "promotion_target_lane": draft.get("promotion_target_lane"),
        "promotion_target_lane_ko": draft.get("promotion_target_lane_ko"),
        "allowed_scope": draft.get("allowed_scope") or [],
        "explicit_not_promoted": draft.get("explicit_not_promoted") or [],
        "ack": ack_info,
        "summary": {
            "discussion_ready": discussion_ready,
            "operator_lane_ready": operator_lane_ready,
            "auto_checks_ok": auto_ok,
            "promotion_rq_acknowledged": promotion_rq_acknowledged,
            "human_signoff_status": signoff.get("human_signoff_status"),
            "gate_decision": gate_summary.get("decision"),
            "evidence_status": evidence.get("status"),
            "outcome_class": (
                "operator_lane_candidate"
                if operator_lane_ready
                else ("discussion_candidate" if discussion_ready else "hold_research")
            ),
            "operator_hint_ko": (
                "RQ-031 운영자 보조 레인 승격 토의 OK — Track A/live/MS 합선 없음 [HYPO]"
                if operator_lane_ready
                else (
                    "RQ-031 토의 준비 OK — 2차 scope ack 대기 [HYPO]"
                    if discussion_ready
                    else "RQ-031 전제 미충족 — RQ-028/029 번들 재실행 [HYPO]"
                )
            ),
        },
        "auto_checks": auto_checks,
        "blockers_ko": blockers,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "note_ko": "operator_lane_ready여도 Track A·live 자동 승격 없음",
        },
        "sources": {
            "draft": str(DEFAULT_DRAFT.relative_to(ROOT)).replace("\\", "/"),
            "checklist_readiness": str(DEFAULT_READINESS.relative_to(ROOT)).replace("\\", "/"),
            "evidence_pack": str(DEFAULT_EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "promotion_gate": str(DEFAULT_GATE.relative_to(ROOT)).replace("\\", "/"),
        },
        "repro_commands": [
            "pwsh -File scripts/Run-ACodePromotionRqDiscussionBundle_v1.ps1",
            "py scripts/build_a_code_promotion_rq_readiness_v1.py",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--checklist", type=Path, default=DEFAULT_READINESS)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    draft = _read(args.draft)
    if draft.get("schema") != "a_code_promotion_rq_draft_v1":
        raise SystemExit(f"invalid draft: {args.draft}")

    report = build_readiness(
        draft=draft,
        checklist=_read(args.checklist),
        evidence=_read(args.evidence),
        gate=_read(args.gate),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = report["summary"]["operator_lane_ready"]
    print(
        f"OK: {args.out} discussion_ready={report['summary']['discussion_ready']} "
        f"operator_lane_ready={ready}"
    )
    if args.strict and not report["summary"]["discussion_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
