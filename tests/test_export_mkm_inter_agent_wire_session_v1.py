"""M12 wire session export smoke."""

from __future__ import annotations


def test_export_wire_session_trading_ok():
    from scripts.export_mkm_inter_agent_wire_session_v1 import export_session

    doc = export_session(scenario="trading", turns=2)
    assert doc.get("ok") is True
    assert doc.get("all_envelopes_schema_valid") is True
    assert doc.get("envelope_count") == 2


def test_http_client_ephemeral_health():
    from scripts.mkm_inter_agent_http_client_v1 import MkmCompressionHttpClient, ephemeral_compression_api_server

    with ephemeral_compression_api_server() as base:
        client = MkmCompressionHttpClient(base)
        r = client.get("/health")
        assert r.status_code == 200


def test_live_http_dialogue_ephemeral():
    from scripts.run_mkm_inter_agent_dialogue_wire_first_live_http_v1 import run_live_dialogue
    from scripts.mkm_inter_agent_http_client_v1 import ephemeral_compression_api_server

    with ephemeral_compression_api_server() as base:
        doc = run_live_dialogue(base_url=base, turns=2, scenario="trading")
        assert doc.get("ok") is True
        assert doc.get("wire_turn_endpoint_ok") is True
