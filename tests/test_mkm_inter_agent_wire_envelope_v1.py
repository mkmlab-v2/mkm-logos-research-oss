"""Wire envelope v1 + runtime adapter smoke."""

from __future__ import annotations


def test_wire_turn_endpoint_returns_envelope():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    r = client.post(
        "/v1/research/mkm_inter_agent_wire/turn",
        json={
            "text": "strong morph greek logos bible reference message kai mercy",
            "turn_id": 1,
            "from_agent": "a",
            "to_agent": "b",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("envelope_schema") == "mkm_inter_agent_wire_envelope_v1"
    env = body.get("envelope") or {}
    assert env.get("schema") == "mkm_inter_agent_wire_envelope_v1"
    assert body.get("envelope_utf8_byte_len", 0) > 0
    assert (env.get("payload") or {}).get("atom_id_count", 0) >= 1


def test_runtime_adapter_roundtrip():
    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app
    from scripts.mkm_inter_agent_wire_envelope_v1 import new_session_id
    from scripts.mkm_inter_agent_wire_runtime_adapter_v1 import receive_turn_wire_v1, send_turn_wire_v1

    client = TestClient(app)
    sid = new_session_id("test")
    sent = send_turn_wire_v1(
        client,
        text="logos bible mercy alpha beta",
        session_id=sid,
        turn_id=1,
        from_agent="alpha",
        to_agent="beta",
    )
    assert sent.get("ok")
    recv = receive_turn_wire_v1(client, sent["envelope"])
    assert recv.get("ok")
