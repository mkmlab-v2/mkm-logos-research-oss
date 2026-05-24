#!/usr/bin/env python3
"""Runtime adapter: plaintext turn -> wire envelope v1 (TestClient or live base URL)."""

from __future__ import annotations

import json
from typing import Any, Protocol

from scripts.mkm_inter_agent_wire_envelope_v1 import build_turn_envelope


class _HttpLike(Protocol):
    def post(self, path: str, json: dict[str, Any]) -> Any: ...


def send_turn_wire_v1(
    client: _HttpLike,
    *,
    text: str,
    session_id: str,
    turn_id: int,
    from_agent: str,
    to_agent: str,
    loss_profile: str = "semantic_general",
    routing_profile: str = "track_a_promoted",
    zstd_min_raw_bytes: int = 0,
    use_ko_health_sidecar: bool = False,
) -> dict[str, Any]:
    """Encode lexicon wire and return turn envelope v1."""
    enc = client.post(
        "/v1/research/mkm_lexicon_wire/encode",
        json={
            "text": text,
            "zstd_min_raw_bytes": zstd_min_raw_bytes,
            "use_ko_health_sidecar": use_ko_health_sidecar,
        },
    )
    if enc.status_code != 200:
        return {
            "ok": False,
            "error": f"encode_status_{enc.status_code}",
            "body": enc.text,
        }
    body = enc.json()
    envelope = build_turn_envelope(
        encode_response=body,
        session_id=session_id,
        turn_id=turn_id,
        from_agent=from_agent,
        to_agent=to_agent,
        loss_profile=loss_profile,
        routing_profile=routing_profile,
    )
    return {"ok": True, "envelope": envelope, "encode": body}


def receive_turn_wire_v1(client: _HttpLike, envelope: dict[str, Any]) -> dict[str, Any]:
    """Decode wire_b64 from envelope payload."""
    payload = envelope.get("payload") or {}
    wire_b64 = payload.get("wire_b64") or ""
    enc_ids = payload.get("atom_id_sequence") or []
    if not isinstance(enc_ids, list):
        enc_ids = []
    if not wire_b64 and len(enc_ids) == 0:
        return {
            "ok": True,
            "decode": {"atom_id_sequence": [], "integrity_flags": {"research_only": True, "empty_lexicon_turn": True}},
            "roundtrip_atom_ids_match": True,
            "empty_lexicon_turn": True,
        }
    dec = client.post("/v1/research/mkm_lexicon_wire/decode", json={"wire_b64": wire_b64})
    if dec.status_code != 200:
        return {"ok": False, "error": f"decode_status_{dec.status_code}"}
    dj = dec.json()
    dec_ids = dj.get("atom_id_sequence") or []
    if len(enc_ids) == 0 and len(dec_ids) == 0:
        return {
            "ok": True,
            "decode": dj,
            "roundtrip_atom_ids_match": True,
            "empty_lexicon_turn": True,
        }
    return {
        "ok": enc_ids == dec_ids and len(enc_ids) > 0,
        "decode": dj,
        "roundtrip_atom_ids_match": enc_ids == dec_ids,
    }
