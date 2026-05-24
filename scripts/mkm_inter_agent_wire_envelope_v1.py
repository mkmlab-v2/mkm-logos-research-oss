"""MKM inter-agent wire envelope v1 — turn metadata + lexicon atom wire payload."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

WIRE_ENVELOPE_SCHEMA = "mkm_inter_agent_wire_envelope_v1"
WIRE_FORMAT_VERSION = "1.0.0"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_turn_envelope(
    *,
    encode_response: dict[str, Any],
    session_id: str,
    turn_id: int,
    from_agent: str,
    to_agent: str,
    loss_profile: str = "semantic_general",
    routing_profile: str = "track_a_promoted",
    client_request_id: str | None = None,
) -> dict[str, Any]:
    """Wrap lexicon wire encode API body into a turn envelope (on-wire JSON contract)."""
    atom_ids = encode_response.get("atom_id_sequence") or []
    if not isinstance(atom_ids, list):
        atom_ids = []
    return {
        "schema": WIRE_ENVELOPE_SCHEMA,
        "wire_format_version": WIRE_FORMAT_VERSION,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "session_id": session_id,
        "turn_id": turn_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "loss_profile": loss_profile,
        "routing_profile": routing_profile,
        "client_request_id": client_request_id or f"wire-v1-{session_id}-turn-{turn_id}",
        "payload": {
            "kind": "lexicon_atom_wire",
            "wire_b64": encode_response.get("wire_b64") or "",
            "wire_byte_len": encode_response.get("wire_byte_len") or 0,
            "codec_variant": encode_response.get("codec_variant") or "none",
            "atom_id_sequence": [str(x) for x in atom_ids],
            "atom_id_count": len(atom_ids),
            "lexicon_meta": encode_response.get("lexicon_meta") or {},
        },
        "integrity_flags": {
            "research_only": True,
            "packet_optional": True,
        },
        "boundary_ack": (
            "Wire-first envelope is B-track research; not production lingua franca or live trading."
        ),
    }


def envelope_utf8_byte_len(envelope: dict[str, Any]) -> int:
    return len(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def new_session_id(prefix: str = "a2a") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
