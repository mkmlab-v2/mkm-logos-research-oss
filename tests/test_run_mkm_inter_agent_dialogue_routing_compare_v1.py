"""Dialogue routing compare (health scenario smoke)."""

from __future__ import annotations

from scripts.run_mkm_inter_agent_dialogue_routing_compare_v1 import run_compare


def test_dialogue_routing_compare_health_smoke() -> None:
    doc = run_compare(turns=2, scenario="health")
    assert doc["schema"] == "mkm_inter_agent_dialogue_routing_compare_v1"
    assert len(doc["runs"]) == 2
    assert all(r.get("all_compress_ok") for r in doc["runs"])
    assert doc["runs"][1].get("routing_profile") == "b_track_domain_relax"
