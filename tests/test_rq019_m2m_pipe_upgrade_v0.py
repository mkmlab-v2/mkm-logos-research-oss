"""RQ-019 M2M pipe upgrade v0 — Trust Packet v0.2 roundtrip + OOV HOLD."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from scripts.mkm_rq019_trust_packet_v02 import (  # noqa: E402
    DEFAULT_CODEBOOK_ID,
    DEFAULT_CODEBOOK_VERSION,
    PACKET_FORMAT_VERSION_V02,
    build_envelope,
    resolve_hold,
    validate_envelope_shape,
)
from scripts.run_rq019_m2m_two_agent_roundtrip_v0 import (  # noqa: E402
    agent_a_encode,
    agent_b_expand,
    run_roundtrip,
)
from scripts.run_policy_allowlist_hold_gate_v0 import (  # noqa: E402
    DEFAULT_ALLOWLIST,
    evaluate,
    load_allowlist,
)

SAMPLE = "M2M Trust Packet v0.2 roundtrip fixture — research_only."


def test_trust_packet_v02_shape_and_pins() -> None:
    env = build_envelope(
        {
            "packet_format_version": "trust_packet.0.1",
            "api_contract_version": "2.0.0-draft",
            "loss_profile": "semantic_general",
            "compressed_text": "x",
            "residual_meta": {},
            "content_fingerprint": "abc",
        },
        codebook_id=DEFAULT_CODEBOOK_ID,
        codebook_version=DEFAULT_CODEBOOK_VERSION,
        allowlist_ref="docs/final/artifacts/policy_allowlist_hold_pilot_franchise_sop_v0_latest.json",
    )
    assert env["packet_format_version"] == PACKET_FORMAT_VERSION_V02
    assert env["research_only"] is True
    assert env["send_gate"] == "HOLD"
    assert env["codebook_id"] == DEFAULT_CODEBOOK_ID
    assert env["codebook_version"] == DEFAULT_CODEBOOK_VERSION
    assert env.get("allowlist_ref")
    assert validate_envelope_shape(env) == []


def test_two_agent_roundtrip_pass() -> None:
    result = run_roundtrip(SAMPLE)
    assert result["send_gate"] == "HOLD"
    assert result["research_only"] is True
    b = result["agent_b"]
    assert b["hold_signal"] is False
    assert b["expanded"] is True
    assert isinstance(b["text"], str) and len(b["text"]) > 0


def test_oov_token_hold_empty_expand() -> None:
    result = run_roundtrip(SAMPLE, inject_oov=True)
    b = result["agent_b"]
    assert b["hold_signal"] is True
    assert b["expanded"] is False
    assert b["text"] == ""
    assert b["hold_decision"]["reason_code"] == "OOV_TOKEN_HOLD"
    assert b["hold_decision"]["send_gate"] == "HOLD"


def test_codebook_pin_mismatch_hold() -> None:
    result = run_roundtrip(SAMPLE, bad_codebook_pin=True)
    b = result["agent_b"]
    assert b["hold_signal"] is True
    assert b["text"] == ""
    assert b["hold_decision"]["reason_code"] == "CODEBOOK_PIN_MISMATCH"


def test_optional_policy_allowlist_compose_hold_without_mutating_domain_a() -> None:
    """Optional compose: OOV query → HOLD; Domain A allowlist file unchanged."""
    allowlist_path = DEFAULT_ALLOWLIST
    before = allowlist_path.read_text(encoding="utf-8")
    result = run_roundtrip(
        SAMPLE,
        policy_query="definitely_not_in_allowlist_xyz_rq019",
        allowlist_path=allowlist_path,
    )
    after = allowlist_path.read_text(encoding="utf-8")
    assert before == after  # Domain A intact
    b = result["agent_b"]
    assert b["hold_signal"] is True
    assert b["text"] == ""
    assert b["hold_decision"]["reason_code"] in {
        "OOV_HOLD",
        "POLICY_ALLOWLIST_HOLD",
    }


def test_resolve_hold_prefers_pin_over_oov() -> None:
    env = build_envelope(
        {"compressed_text": "z", "residual_meta": {}},
        codebook_id="wrong",
        codebook_version="wrong",
        oov_tokens=["__OOV__"],
    )
    hold = resolve_hold(env)
    assert hold is not None
    assert hold["reason_code"] == "CODEBOOK_PIN_MISMATCH"


def test_schema_file_exists() -> None:
    path = ROOT / "docs/final/schemas/mkm_trust_packet_envelope_v0_2.schema.json"
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("title") or doc.get("$id")
    props = doc.get("properties") or {}
    assert "packet_format_version" in props
    assert "codebook_id" in props
    assert "codebook_version" in props


def test_agent_a_encode_agent_b_expand_direct() -> None:
    env = agent_a_encode(SAMPLE)
    assert env["packet_format_version"] == PACKET_FORMAT_VERSION_V02
    b = agent_b_expand(env)
    assert b["expanded"] is True
    assert b["send_gate"] == "HOLD"


def test_domain_a_allowlist_gate_still_hold_on_oov() -> None:
    """Sanity: Domain A gate behavior unchanged (companion belt)."""
    doc = load_allowlist(DEFAULT_ALLOWLIST)
    audit = evaluate(doc, "not_an_allowed_phrase_or_id")
    assert audit["decision"] == "HOLD"
    assert audit["reason_code"] == "OOV_HOLD"
    assert audit["send_gate"] == "HOLD"
