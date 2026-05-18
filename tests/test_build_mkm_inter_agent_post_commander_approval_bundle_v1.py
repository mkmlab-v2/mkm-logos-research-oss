"""Post-commander-approval ops bundle smoke."""

from __future__ import annotations

from scripts.build_mkm_inter_agent_post_commander_approval_bundle_v1 import build


def test_post_approval_bundle_ops_ready() -> None:
    doc = build(dialogue_turns=2)
    assert doc["commander_approved"] is True
    assert doc["rq_019_external_closed"] is False
    assert doc["ops_ready"]["b_track_health_dialogue"] is True
    assert doc["ops_ready"]["routing_profile"] == "b_track_domain_relax"
