"""MKM inter-agent A2A dialogue mock (Trust Packet only)."""

from __future__ import annotations

from scripts.run_mkm_inter_agent_dialogue_mock_v1 import run_dialogue


def test_dialogue_mock_two_turns_packet_only() -> None:
    doc = run_dialogue(turns=2)
    assert doc["all_compress_ok"] is True
    assert doc["all_expand_ok"] is True
    assert doc["turns_recorded"] == 2
    t1 = doc["transcript"][0]
    assert t1["wire_only"] is True
    assert t1["compress"]["http_status"] == 200
    assert "expand_inbound_packet_only" not in t1
    t2 = doc["transcript"][1]
    assert t2.get("expand_inbound_packet_only", {}).get("original_text_on_request") is False


def test_dialogue_mock_summary_schema_fields() -> None:
    doc = run_dialogue(turns=2)
    assert doc["schema"] == "mkm_inter_agent_dialogue_mock_summary_v1"
    assert doc["hypothesis_tier"] == "B"
    assert "Trust Packet" in doc["boundary_ack"]
