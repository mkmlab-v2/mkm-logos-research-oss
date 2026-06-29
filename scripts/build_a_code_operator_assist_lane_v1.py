#!/usr/bin/env python3
"""RQ-031: freeze operator-assist lane status artifact ([HYPO] · non-gating)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/a_code_operator_assist_lane_v1_latest.json"
DEFAULT_DRAFT = ROOT / "experiments/a_code_12ai_v2/specs/a_code_promotion_rq_draft_v1.json"
DEFAULT_READINESS = ROOT / "reports/a_code_promotion_rq_readiness_v1_latest.json"
DEFAULT_CHECKLIST = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"
DEFAULT_EVIDENCE = ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json"
DEFAULT_ACK_ARTIFACT = ROOT / "docs/final/artifacts/a_code_promotion_rq_commander_ack_v1_latest.json"
DEFAULT_MIGRATION_DRAFT = ROOT / "docs/final/artifacts/a_code_constitution_worklist_migration_draft_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def build_lane_doc() -> dict[str, Any]:
    draft = _read(DEFAULT_DRAFT)
    promotion_rq = _read(DEFAULT_READINESS)
    checklist = _read(DEFAULT_CHECKLIST)
    evidence = _read(DEFAULT_EVIDENCE)
    ack_artifact = _read(DEFAULT_ACK_ARTIFACT)
    migration = _read(DEFAULT_MIGRATION_DRAFT)

    prq_summary = promotion_rq.get("summary") or {}
    checklist_summary = checklist.get("summary") or {}
    operator_ready = prq_summary.get("operator_lane_ready") is True

    wired_surfaces = [
        {
            "id": "evening_briefing_tg",
            "script": "scripts/score_commander_evening_briefing_v1.py",
            "append_helper": "scripts/a_code_evening_briefing_append_v1.py",
            "tag": "[HYPO·non-gating]",
        },
        {
            "id": "dev_day_pack",
            "script": "scripts/build_commander_dev_day_pack_v1.py",
            "field": "a_code_governor_note",
            "tag": "[HYPO·non-gating]",
        },
        {
            "id": "trackc_dashboard",
            "script": "scripts/build_mkm_trackc_ops_dashboard_v1.py",
            "field": "trackc.a_code_governor",
            "tag": "[HYPO·non-gating]",
        },
        {
            "id": "hero_evening_thin_bundle",
            "script": "scripts/Invoke-CommanderDailyProphecyHeroLoop_v1.ps1",
            "bundle": "scripts/Run-ACodeGovernorResearchBundle_v1.ps1 -SkipMultiday",
            "tag": "[HYPO·non-gating]",
        },
        {
            "id": "trackc_macro_fusion_oneline",
            "script": "scripts/Invoke-TrackCMacroDailyFusion_v1.ps1",
            "helper": "scripts/print_a_code_governor_trackc_oneline_v1.py",
            "tag": "[HYPO·non-gating]",
        },
        {
            "id": "constitution_pointer_pr_draft",
            "script": "scripts/build_a_code_constitution_pointer_pr_draft_v1.py",
            "artifact_md": "reports/a_code_constitution_pointer_pr_draft_v1_latest.md",
            "tag": "[HYPO·human PR only]",
        },
    ]

    return {
        "schema": "a_code_operator_assist_lane_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_ids": {
            "research_sandbox": "RQ-028",
            "checklist": "RQ-029",
            "operator_lane": "RQ-031",
        },
        "hypothesis_tier": "B",
        "research_only": True,
        "lane_status": "OPERATOR_ASSIST_FIXED" if operator_ready else "HOLD_RESEARCH",
        "non_gating": True,
        "operator_lane_ready": operator_ready,
        "promotion_discussion_eligible": checklist_summary.get("promotion_discussion_eligible"),
        "mechanical_ready": checklist_summary.get("mechanical_ready"),
        "human_signoff_status": checklist_summary.get("human_signoff_status"),
        "evidence_status": evidence.get("status"),
        "gate_decision": checklist_summary.get("gate_decision"),
        "promotion_target_lane": draft.get("promotion_target_lane"),
        "allowed_scope": draft.get("allowed_scope") or [],
        "explicit_not_promoted": draft.get("explicit_not_promoted") or [],
        "wired_surfaces": wired_surfaces,
        "routine_commands": [
            "pwsh -File scripts/Run-ACodeOperatorAssistLaneRoutine_v1.ps1",
            "pwsh -File scripts/Run-ACodePromotionRqDiscussionBundle_v1.ps1",
            "pwsh -File scripts/Run-ACodeGovernorResearchBundle_v1.ps1 -SkipMultiday",
            "pwsh -File scripts/Register-ACodeOperatorAssistLaneWeeklyTask_v1.ps1",
            "py scripts/build_a_code_constitution_pointer_pr_draft_v1.py",
        ],
        "ack_reference": ack_artifact.get("ack_reference"),
        "migration_draft_ready": migration.get("schema") == "a_code_constitution_worklist_migration_draft_v1",
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_auto_trigger": False,
            "constitution_auto_edit": False,
            "note_ko": "운영자 보조 레인 고정. Track A·live·MS·CONSTITUTION 자동 합선 없음.",
        },
        "operator_hint_ko": (
            "RQ-031 운영자 보조 레인 고정 — evening/TG·dev pack·dashboard만 [HYPO·non-gating]"
            if operator_ready
            else "operator_lane_ready=false — promotion rq 번들 재실행"
        ),
        "sources": {
            "promotion_rq_draft": _rel(DEFAULT_DRAFT),
            "promotion_rq_readiness": _rel(DEFAULT_READINESS),
            "checklist_readiness": _rel(DEFAULT_CHECKLIST),
            "evidence_pack": _rel(DEFAULT_EVIDENCE),
            "commander_ack_artifact": _rel(DEFAULT_ACK_ARTIFACT),
            "migration_draft": _rel(DEFAULT_MIGRATION_DRAFT),
            "operating_spec": "docs/final/protocols/A_CODE_12AI_AUTONOMOUS_OPERATING_SPEC_V2.md",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    doc = build_lane_doc()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = doc.get("operator_lane_ready")
    print(f"OK: {args.out} lane_status={doc.get('lane_status')} operator_lane_ready={ready}")
    if args.strict and not ready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
