"""Oracle Logos Tier-2 incremental append gate evaluation ([HYPO] / B-track).

Evaluates blocker release matrix without auto-unlocking Track A or live trading.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

READINESS_REL = "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
PROTOCOL_REL = "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"
SIGNOFF_REL = "docs/final/artifacts/logos_oracle_tier2_pin_schema_freeze_signoff_v1_latest.json"
AUDIT_REL = "docs/final/artifacts/logos_oracle_tier2_public_facing_audit_v1_latest.json"
SIDECAR_REL = "storage/meta/mkm_sidecar_constitution_paths_v1.json"
PUBLIC_FACING_REL = "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
CONSTITUTION_POINTER = (
    "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
    " — Logos ops memory Cursor inject 보강 (2026-06-19)"
)
LOGOS_SIDECAR_SEGMENT_ID = "logos_ops_memory_cursor_inject"
SIGNOFF_SCHEMA_REL = "docs/final/schemas/logos_oracle_tier2_pin_schema_freeze_signoff_v1.schema.json"
AUDIT_SCHEMA_REL = "docs/final/schemas/logos_oracle_tier2_public_facing_audit_v1.schema.json"

REPRO_ONE_SHOT = "py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pin_schema_snapshot_sha256(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def validate_signoff_doc(doc: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    errors = _schema_errors(doc, root / SIGNOFF_SCHEMA_REL)
    wall = doc.get("track_wall") or {}
    if wall.get("track_a_auto_promotion") is not False:
        errors.append("track_wall.track_a_auto_promotion must be false")
    if wall.get("live_trading_auto_trigger") is not False:
        errors.append("track_wall.live_trading_auto_trigger must be false")
    if wall.get("promotion_cascade_forbidden") is not True:
        errors.append("track_wall.promotion_cascade_forbidden must be true")
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
            "incremental_append_only_no_constitution_full_rewrite",
            "no_track_a_live_auto_merge",
            "promotion_cascade_forbidden_ack",
        ):
            if attest.get(key) is not True:
                errors.append(f"attestations.{key} must be true when approved=true")
    return errors


def validate_audit_doc(doc: dict[str, Any], *, root: Path = ROOT) -> list[str]:
    errors = _schema_errors(doc, root / AUDIT_SCHEMA_REL)
    if doc.get("checklist_ssot") != PUBLIC_FACING_REL:
        errors.append(f"checklist_ssot must be {PUBLIC_FACING_REL}")
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
            "artifact_bound_copy_only",
        ):
            if attest.get(key) is not True:
                errors.append(f"attestations.{key} must be true when audit_pass=true")
    return errors


def evaluate_blocker_gates(*, root: Path = ROOT) -> dict[str, Any]:
    readiness = _read_json(root / READINESS_REL) or {}
    signoff = _read_json(root / SIGNOFF_REL)
    audit = _read_json(root / AUDIT_REL)
    sidecar = _read_json(root / SIDECAR_REL) or {}

    snap = readiness.get("tier2_pin_schema_snapshot") or {}
    snap_sha = pin_schema_snapshot_sha256(snap) if snap else None
    signoff_errors = validate_signoff_doc(signoff, root=root) if signoff else ["signoff artifact missing"]
    audit_errors = validate_audit_doc(audit, root=root) if audit else ["audit artifact missing"]

    signoff_ok = signoff is not None and not signoff_errors
    audit_ok = audit is not None and not audit_errors
    signoff_approved = bool(signoff and signoff.get("approved")) and signoff_ok
    audit_pass = bool(audit and audit.get("audit_pass")) and audit_ok

    send_gate_open = signoff_approved and (signoff or {}).get("send_gate") == "OPEN"
    tier2_prep_ready = bool(readiness.get("tier2_prep_ready"))
    pin_ref = (signoff or {}).get("pin_schema_snapshot_ref") or {}
    pin_hash_match = bool(
        snap_sha
        and pin_ref.get("snapshot_sha256") == snap_sha
        and pin_ref.get("artifact") == READINESS_REL
    )
    logos_segment = (sidecar.get("segments") or {}).get(LOGOS_SIDECAR_SEGMENT_ID)
    sidecar_logos_segment_ok = logos_segment is not None
    sidecar_present = sidecar.get("schema") == "mkm_sidecar_constitution_paths_v1"

    promotion_cascade_wall_ok = bool(
        signoff_approved
        and ((signoff or {}).get("track_wall") or {}).get("promotion_cascade_forbidden") is True
        and ((signoff or {}).get("attestations") or {}).get("promotion_cascade_forbidden_ack") is True
    )

    blockers: list[dict[str, Any]] = [
        {
            "blocker_id": "send_gate_hold",
            "label": "send_gate: HOLD — human release required for external narrative",
            "release_condition_ko": "signoff approved=true AND send_gate=OPEN (지휘관 명시)",
            "released": send_gate_open,
            "evidence": {
                "signoff_present": signoff is not None,
                "signoff_approved": signoff_approved,
                "send_gate": (signoff or {}).get("send_gate"),
            },
        },
        {
            "blocker_id": "promotion_cascade_forbidden",
            "label": "promotion_cascade_forbidden — Logos structural gates ≠ Track A",
            "release_condition_ko": "영구 격벽 유지 — Tier-2는 pointer 확장만; track_wall.promotion_cascade_forbidden=true 서명",
            "released": promotion_cascade_wall_ok,
            "evidence": {
                "wall_ack_signed": promotion_cascade_wall_ok,
                "note": "released=true means wall acknowledged — NOT Track A unlock",
            },
        },
        {
            "blocker_id": "pin_schema_freeze_signoff",
            "label": "tier2_full_rules_upgrade blocked until send_gate OPEN + pin schema freeze sign-off",
            "release_condition_ko": "signoff approved + pin_schema_snapshot_ref.snapshot_sha256 == readiness snapshot",
            "released": signoff_approved and pin_hash_match and send_gate_open,
            "evidence": {
                "snapshot_sha256_current": snap_sha,
                "snapshot_sha256_signoff": pin_ref.get("snapshot_sha256"),
                "pin_hash_match": pin_hash_match,
            },
        },
        {
            "blocker_id": "constitution_full_rewrite_ban",
            "label": "CONSTITUTION full rewrite requires D1 commander intent + PUBLIC_FACING audit",
            "release_condition_ko": "incremental append only — sidecar logos segment + audit_pass + commander_intent_d1 on signoff",
            "released": (
                signoff_approved
                and audit_pass
                and sidecar_logos_segment_ok
                and bool(str((signoff or {}).get("commander_intent_d1") or "").strip())
                and ((signoff or {}).get("attestations") or {}).get(
                    "incremental_append_only_no_constitution_full_rewrite"
                )
                is True
            ),
            "evidence": {
                "sidecar_logos_segment_ok": sidecar_logos_segment_ok,
                "audit_pass": audit_pass,
                "constitution_pointer": CONSTITUTION_POINTER,
            },
        },
    ]

    tier2_unlock_ready = all(b["released"] for b in blockers)

    return {
        "tier2_prep_ready": tier2_prep_ready,
        "tier2_cursor_rules_full_upgrade_ready": tier2_unlock_ready,
        "tier3_constitution_narrative_full_upgrade_ready": False,
        "send_gate": (signoff or {}).get("send_gate") or readiness.get("send_gate") or "HOLD",
        "pin_schema_snapshot_sha256": snap_sha,
        "signoff_validation_errors": signoff_errors if signoff else ["signoff artifact missing"],
        "audit_validation_errors": audit_errors if audit else ["audit artifact missing"],
        "sidecar_present": sidecar_present,
        "sidecar_logos_segment_ok": sidecar_logos_segment_ok,
        "blocker_release_matrix": blockers,
        "incremental_append_steps": [
            {
                "step": 1,
                "action": "CONSTITUTION anchor append (existing 2026-06-19 block — no body replace)",
                "artifact": CONSTITUTION_POINTER,
            },
            {
                "step": 2,
                "action": "Rebuild constitution path sidecar with logos_ops_memory_cursor_inject segment",
                "command": "py scripts/build_mkm_sidecar_constitution_paths_v1.py",
            },
            {
                "step": 3,
                "action": "Commander pin-freeze signoff JSON (template → latest, set approved=true)",
                "template": "docs/final/artifacts/logos_oracle_tier2_pin_schema_freeze_signoff_v1.template.json",
                "latest": SIGNOFF_REL,
                "validate": "py scripts/validate_logos_oracle_tier2_pin_schema_freeze_signoff_v1.py",
            },
            {
                "step": 4,
                "action": "PUBLIC_FACING engineering audit record",
                "checklist": PUBLIC_FACING_REL,
                "template": "docs/final/artifacts/logos_oracle_tier2_public_facing_audit_v1.template.json",
                "latest": AUDIT_REL,
                "validate": "py scripts/validate_logos_oracle_tier2_public_facing_audit_v1.py",
            },
        ],
        "repro_one_shot": REPRO_ONE_SHOT,
    }


def build_protocol_document(*, root: Path = ROOT) -> dict[str, Any]:
    gates = evaluate_blocker_gates(root=root)
    return {
        "schema": "logos_oracle_tier2_incremental_append_protocol_v1",
        "version": "1.0.0",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": (
            "[HYPO] Tier-2 incremental append protocol — sidecar slices + pointer inject only; "
            "CONSTITUTION MD remains SSOT; no full rewrite; no Track A·live auto merge"
        ),
        "readiness_artifact": READINESS_REL,
        "signoff_artifact": SIGNOFF_REL,
        "audit_artifact": AUDIT_REL,
        "sidecar_artifact": SIDECAR_REL,
        "tier2_cursor_rules_full_upgrade_ready": gates["tier2_cursor_rules_full_upgrade_ready"],
        "tier3_constitution_narrative_full_upgrade_ready": False,
        "send_gate": gates["send_gate"],
        "pin_schema_snapshot_sha256": gates["pin_schema_snapshot_sha256"],
        "blocker_release_matrix": gates["blocker_release_matrix"],
        "incremental_append_steps": gates["incremental_append_steps"],
        "signoff_validation_errors": gates["signoff_validation_errors"],
        "audit_validation_errors": gates["audit_validation_errors"],
        "repro_one_shot": REPRO_ONE_SHOT,
        "commander_unlock_sequence_ko": [
            "1) tier1 readiness 9/9 + tier2_prep_ready 유지",
            "2) sidecar logos segment rebuild",
            "3) template→latest signoff (approved=true, send_gate=OPEN, snapshot_sha256 일치)",
            "4) PUBLIC_FACING audit_pass=true 기록",
            "5) py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py → tier2 flag flip",
        ],
    }
