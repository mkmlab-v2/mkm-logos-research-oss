# @MKM12-METADATA
# Type: Logic
# Purpose: v2 API graph_wire_selective_bridge research flag.

from __future__ import annotations

from fastapi.testclient import TestClient

from scripts.compression_token_api_v2_stub import app

client = TestClient(app)


def test_v2_compress_graph_wire_selective_bridge_flags():
    sample = (
        "State 3 to 11 dominates bootstrap data babel empire transition "
        "read only cannot trigger policy"
    )
    cr = client.post(
        "/v2/compress",
        json={
            "text": sample,
            "loss_profile": "semantic_general",
            "compression_profile": "economy",
            "emit_semantic_pointer": True,
            "graph_wire_selective_bridge": True,
        },
    )
    assert cr.status_code == 200
    flags = cr.json().get("integrity_flags") or {}
    stub = cr.json()["compression_packet"]["residual_meta"]["mk_stub_v2"]
    sp = stub.get("semantic_pointer") or {}
    gw = sp.get("graph_wire_influence_v1")
    if gw:
        assert flags.get("graph_wire_influence_v1") is True
        assert "wire_influence_score" in gw
