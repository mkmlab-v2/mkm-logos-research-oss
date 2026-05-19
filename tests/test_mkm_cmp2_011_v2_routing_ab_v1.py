"""cmp2_011 focused routing A/B smoke."""

from __future__ import annotations

from scripts.run_mkm_cmp2_011_v2_routing_ab_v1 import run_ab


def test_cmp2_011_routing_ab_three_profiles() -> None:
    doc = run_ab()
    assert doc["case_id"] == "cmp2_011"
    assert len(doc["rows"]) == 3
    assert all(r.get("http_status") == 200 for r in doc["rows"])
