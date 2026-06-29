"""Oracle Logos Tier-3 narrative upgrade gate evaluation ([HYPO] / B-track).

Tier-3 = CONSTITUTION narrative append + A2A parallel-chat wire — NOT full rewrite.
Requires Tier-2 unlock first; separate commander + legal review gates.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from logos_oracle_tier2_incremental_append_lib_v1 import (
    PROTOCOL_REL,
    READINESS_REL,
    evaluate_blocker_gates,
)

ROOT = Path(__file__).resolve().parents[1]

TIER3_PROTOCOL_REL = "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"
TIER3_SIGNOFF_REL = "docs/final/artifacts/logos_oracle_tier3_narrative_commander_signoff_v1_latest.json"
TIER3_LEGAL_AUDIT_REL = "docs/final/artifacts/logos_oracle_tier3_public_facing_legal_audit_v1_latest.json"
A2A_ORACLE_BRIEF_REL = "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_oracle_v1_latest.md"
A2A_ORACLE_PILOT_REL = "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_pilot_oracle_v1_latest.json"
TIER3_SIGNOFF_SCHEMA_REL = "docs/final/schemas/logos_oracle_tier3_narrative_commander_signoff_v1.schema.json"
TIER3_LEGAL_SCHEMA_REL = "docs/final/schemas/logos_oracle_tier3_public_facing_legal_audit_v1.schema.json"
REPRO_ONE_SHOT = "py scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _schema_errors(doc: dict[str, Any], schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return [f"schema missing: {schema_path}"]
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema package required"]
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    validator = jsonschema.Draft7Validator(schema)
    return [f"schema:{err.message}" for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path))]


def validate_tier3_signoff_doc(doc: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    errors = _schema_errors(doc, root / TIER3_SIGNOFF_SCHEMA_REL)
    wall = doc.get("track_wall") or {}
    if wall.get("track_a_auto_promotion") is not False:
        errors.append("track_wall.track_a_auto_promotion must be false")
    if wall.get("live_trading_auto_trigger") is not False:
        errors.append("track_wall.live_trading_auto_trigger must be false")
    if doc.get("approved") is True:
        if not str(doc.get("signoff_by") or "").strip():
            errors.append("signoff_by required when approved=true")
        if not doc.get("signoff_utc"):
            errors.append("signoff_utc required when approved=true")
        if not str(doc.get("commander_intent_d1") or "").strip():
            errors.append("commander_intent_d1 required when approved=true")
        attest = doc.get("attestations") or {}
        for key in (
            "human_commander_signoff",
            "narrative_append_only_no_full_rewrite",
            "no_track_a_live_auto_merge",
            "tier2_prerequisite_ack",
        ):
            if attest.get(key) is not True:
                errors.append(f"attestations.{key} must be true when approved=true")
    return errors


def validate_tier3_legal_audit_doc(doc: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    errors = _schema_errors(doc, root / TIER3_LEGAL_SCHEMA_REL)
    if doc.get("audit_pass") is True:
        if not str(doc.get("auditor") or "").strip():
            errors.append("auditor required when audit_pass=true")
        if not doc.get("audit_utc"):
            errors.append("audit_utc required when audit_pass=true")
        attest = doc.get("attestations") or {}
        for key in (
            "no_bible_ai_evolution_complete_claim",
            "logos_non_gating_ack",
            "no_track_a_live_implication",
            "legal_review_not_substitute_for_counsel",
        ):
            if attest.get(key) is not True:
                errors.append(f"attestations.{key} must be true when audit_pass=true")
    return errors


def evaluate_tier3_gates(*, root: Path = ROOT) -> dict[str, Any]:
    tier2_eval = evaluate_blocker_gates(root=root)
    tier2_unlock = bool(tier2_eval.get("tier2_cursor_rules_full_upgrade_ready"))
    signoff = _read_json(root / TIER3_SIGNOFF_REL)
    legal = _read_json(root / TIER3_LEGAL_AUDIT_REL)
    a2a_brief_ok = (root / A2A_ORACLE_BRIEF_REL).is_file()
    a2a_pilot_ok = (root / A2A_ORACLE_PILOT_REL).is_file()

    signoff_errors = validate_tier3_signoff_doc(signoff, root=root) if signoff else ["signoff artifact missing"]
    legal_errors = validate_tier3_legal_audit_doc(legal, root=root) if legal else ["legal audit artifact missing"]
    signoff_ok = signoff is not None and not signoff_errors
    legal_ok = legal is not None and not legal_errors
    signoff_approved = bool(signoff and signoff.get("approved")) and signoff_ok
    legal_pass = bool(legal and legal.get("audit_pass")) and legal_ok

    blockers: list[dict[str, Any]] = [
        {
            "blocker_id": "tier2_prerequisite",
            "label": "Tier-2 incremental append must be unlocked first",
            "release_condition_ko": "tier2_cursor_rules_full_upgrade_ready=true",
            "released": tier2_unlock,
            "evidence": {"tier2_unlock": tier2_unlock, "tier2_protocol": PROTOCOL_REL},
        },
        {
            "blocker_id": "tier3_narrative_commander_signoff",
            "label": "Tier-3 narrative CONSTITUTION append requires separate commander sign-off",
            "release_condition_ko": "logos_oracle_tier3_narrative_commander_signoff approved=true",
            "released": signoff_approved,
            "evidence": {"signoff_present": signoff is not None, "signoff_approved": signoff_approved},
        },
        {
            "blocker_id": "tier3_public_facing_legal_audit",
            "label": "Tier-3 requires PUBLIC_FACING legal review record (stronger than Tier-2 engineering cross-check)",
            "release_condition_ko": "logos_oracle_tier3_public_facing_legal_audit audit_pass=true",
            "released": legal_pass,
            "evidence": {"legal_audit_present": legal is not None, "audit_pass": legal_pass},
        },
        {
            "blocker_id": "a2a_tier3_wire_handoff_oracle",
            "label": "A2A Tier-3 parallel-chat wire handoff brief+pilot for oracle lane",
            "release_condition_ko": "a2a_tier3_cursor_wire_handoff brief+pilot oracle artifacts present",
            "released": a2a_brief_ok and a2a_pilot_ok,
            "evidence": {"brief_ok": a2a_brief_ok, "pilot_ok": a2a_pilot_ok},
        },
    ]

    tier3_unlock = tier2_unlock and all(b["released"] for b in blockers)

    return {
        "tier2_cursor_rules_full_upgrade_ready": tier2_unlock,
        "tier3_constitution_narrative_full_upgrade_ready": tier3_unlock,
        "tier2_protocol": PROTOCOL_REL,
        "signoff_validation_errors": signoff_errors if signoff else ["signoff artifact missing"],
        "legal_audit_validation_errors": legal_errors if legal else ["legal audit artifact missing"],
        "blocker_release_matrix": blockers,
        "incremental_narrative_steps": [
            {
                "step": 1,
                "action": "Confirm Tier-2 unlock",
                "command": "py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py --require-tier2-unlock",
            },
            {
                "step": 2,
                "action": "Refresh A2A Tier-3 oracle wire handoff",
                "command": "py scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py --lane oracle",
            },
            {
                "step": 3,
                "action": "Commander Tier-3 narrative signoff (template → latest)",
                "template": "docs/final/artifacts/logos_oracle_tier3_narrative_commander_signoff_v1.template.json",
                "latest": TIER3_SIGNOFF_REL,
            },
            {
                "step": 4,
                "action": "PUBLIC_FACING legal audit record",
                "template": "docs/final/artifacts/logos_oracle_tier3_public_facing_legal_audit_v1.template.json",
                "latest": TIER3_LEGAL_AUDIT_REL,
            },
        ],
        "repro_one_shot": REPRO_ONE_SHOT,
    }


def build_protocol_document(*, root: Path = ROOT) -> dict[str, Any]:
    gates = evaluate_tier3_gates(root=root)
    return {
        "schema": "logos_oracle_tier3_narrative_upgrade_protocol_v1",
        "version": "1.0.0",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] Tier-3 narrative upgrade — CONSTITUTION narrative append + A2A wire only; "
            "NOT full rewrite; NOT Track A; NOT live trading"
        ),
        "readiness_artifact": READINESS_REL,
        "tier2_protocol_artifact": PROTOCOL_REL,
        "signoff_artifact": TIER3_SIGNOFF_REL,
        "legal_audit_artifact": TIER3_LEGAL_AUDIT_REL,
        "a2a_oracle_brief": A2A_ORACLE_BRIEF_REL,
        "a2a_oracle_pilot": A2A_ORACLE_PILOT_REL,
        "tier3_constitution_narrative_full_upgrade_ready": gates["tier3_constitution_narrative_full_upgrade_ready"],
        "tier2_prerequisite_met": gates["tier2_cursor_rules_full_upgrade_ready"],
        "blocker_release_matrix": gates["blocker_release_matrix"],
        "incremental_narrative_steps": gates["incremental_narrative_steps"],
        "signoff_validation_errors": gates["signoff_validation_errors"],
        "legal_audit_validation_errors": gates["legal_audit_validation_errors"],
        "repro_one_shot": REPRO_ONE_SHOT,
    }
