"""Legal handoff pack schema smoke."""

from __future__ import annotations

from scripts.build_mkm_inter_agent_legal_handoff_pack_v1 import build


def test_legal_handoff_pack_pending_legal() -> None:
    doc = build()
    assert doc["legal_review_status"] in ("PENDING", "SUBMITTED_TO_COUNSEL", "COUNSEL_SIGNED")
    assert doc["rq_019_status"] == "OPEN"
    assert doc["commander_ops_approved"] is True
    assert len(doc["checklist"]) >= 7
    assert doc["checklist"][6]["met"] is False
