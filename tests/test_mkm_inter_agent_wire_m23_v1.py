"""M23: Live HTTP health sidecar + milestone artifact index."""

from __future__ import annotations


def test_health_sidecar_live_http_ephemeral():
    from scripts.capture_mkm_inter_agent_health_wire_sidecar_live_http_v1 import capture

    doc = capture(turns=2)
    assert doc.get("ok")
    assert doc.get("avg_atom_id_count", 0) > 1.0


def test_rq019_milestone_index():
    from scripts.build_mkm_inter_agent_rq019_milestone_artifact_index_v1 import build_index

    doc = build_index()
    assert doc.get("ok")
    assert doc.get("milestone_count", 0) >= 20
