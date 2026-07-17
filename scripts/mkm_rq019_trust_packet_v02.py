#!/usr/bin/env python3
"""RQ-019 Trust Packet envelope v0.2 — internal M2M research rail only.

Wraps existing v2 stub compression_packet with codebook pin + optional
allowlist/hold sidecar. Does NOT bump production stub PACKET_FORMAT_VERSION.
Track B · research_only · send_gate HOLD. Not multimodal / M2M-100 / Track C.
"""
from __future__ import annotations

from typing import Any

PACKET_FORMAT_VERSION_V02 = "trust_packet.0.2"
ENVELOPE_SCHEMA = "mkm_trust_packet_envelope_v0_2"
INNER_PACKET_FORMAT = "trust_packet.0.1"  # existing stub contract (unchanged)

# Default research pin — not a production SLA claim.
DEFAULT_CODEBOOK_ID = "master_codebook_lexicon_v1"
DEFAULT_CODEBOOK_VERSION = "research_pin_v0"


def build_envelope(
    compression_packet: dict[str, Any],
    *,
    codebook_id: str = DEFAULT_CODEBOOK_ID,
    codebook_version: str = DEFAULT_CODEBOOK_VERSION,
    allowlist_ref: str | None = None,
    hold_decision: dict[str, Any] | None = None,
    agent_id: str = "agent_a",
    oov_tokens: list[str] | None = None,
) -> dict[str, Any]:
    """Build Trust Packet v0.2 envelope around an existing v0.1 compression_packet."""
    env: dict[str, Any] = {
        "schema": ENVELOPE_SCHEMA,
        "packet_format_version": PACKET_FORMAT_VERSION_V02,
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tag": "[HYPO]",
        "codebook_id": codebook_id,
        "codebook_version": codebook_version,
        "agent_id": agent_id,
        "inner_packet_format_version": INNER_PACKET_FORMAT,
        "compression_packet": compression_packet,
    }
    if allowlist_ref is not None:
        env["allowlist_ref"] = allowlist_ref
    if hold_decision is not None:
        env["hold_decision"] = hold_decision
    if oov_tokens:
        env["oov_tokens"] = list(oov_tokens)
    return env


def validate_envelope_shape(env: dict[str, Any]) -> list[str]:
    """Return list of shape errors (empty = ok)."""
    errs: list[str] = []
    if env.get("schema") != ENVELOPE_SCHEMA:
        errs.append(f"schema_mismatch:{env.get('schema')}")
    if env.get("packet_format_version") != PACKET_FORMAT_VERSION_V02:
        errs.append(f"packet_format_version_mismatch:{env.get('packet_format_version')}")
    if env.get("research_only") is not True:
        errs.append("research_only_required")
    if env.get("send_gate") != "HOLD":
        errs.append("send_gate_must_HOLD")
    if not env.get("codebook_id"):
        errs.append("codebook_id_required")
    if not env.get("codebook_version"):
        errs.append("codebook_version_required")
    pkt = env.get("compression_packet")
    if not isinstance(pkt, dict):
        errs.append("compression_packet_required")
    elif not pkt.get("compressed_text"):
        errs.append("compression_packet.compressed_text_required")
    return errs


def check_codebook_pin(
    env: dict[str, Any],
    *,
    expected_id: str = DEFAULT_CODEBOOK_ID,
    expected_version: str = DEFAULT_CODEBOOK_VERSION,
) -> dict[str, Any] | None:
    """Return HOLD decision if codebook pin mismatches; else None."""
    got_id = str(env.get("codebook_id") or "")
    got_ver = str(env.get("codebook_version") or "")
    if got_id != expected_id or got_ver != expected_version:
        return {
            "decision": "HOLD",
            "reason_code": "CODEBOOK_PIN_MISMATCH",
            "reason_text": (
                f"expected {expected_id}@{expected_version}; "
                f"got {got_id}@{got_ver}"
            ),
            "research_only": True,
            "send_gate": "HOLD",
        }
    return None


def check_oov_tokens(env: dict[str, Any]) -> dict[str, Any] | None:
    """Return HOLD decision if envelope carries unknown/OOV tokens; else None."""
    tokens = env.get("oov_tokens") or []
    if isinstance(tokens, list) and len(tokens) > 0:
        return {
            "decision": "HOLD",
            "reason_code": "OOV_TOKEN_HOLD",
            "reason_text": "Unknown tokens on wire — invent forbidden; expand empty.",
            "oov_tokens": list(tokens),
            "research_only": True,
            "send_gate": "HOLD",
        }
    return None


def resolve_hold(
    env: dict[str, Any],
    *,
    expected_codebook_id: str = DEFAULT_CODEBOOK_ID,
    expected_codebook_version: str = DEFAULT_CODEBOOK_VERSION,
    policy_hold: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Compose HOLD signals: pin mismatch → OOV → optional policy sidecar → envelope hold."""
    pin = check_codebook_pin(
        env,
        expected_id=expected_codebook_id,
        expected_version=expected_codebook_version,
    )
    if pin is not None:
        return pin
    oov = check_oov_tokens(env)
    if oov is not None:
        return oov
    if policy_hold is not None and str(policy_hold.get("decision") or "").upper() == "HOLD":
        return {
            "decision": "HOLD",
            "reason_code": str(policy_hold.get("reason_code") or "POLICY_ALLOWLIST_HOLD"),
            "reason_text": str(
                policy_hold.get("reason_text")
                or "Optional Domain A allowlist compose returned HOLD."
            ),
            "allowlist_ref": env.get("allowlist_ref"),
            "research_only": True,
            "send_gate": "HOLD",
            "compose_note": "Domain A belt optional; not merged commercial product.",
        }
    existing = env.get("hold_decision")
    if isinstance(existing, dict) and str(existing.get("decision") or "").upper() == "HOLD":
        return {
            **existing,
            "research_only": True,
            "send_gate": "HOLD",
        }
    return None
