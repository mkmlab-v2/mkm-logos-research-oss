"""Health domain signoff candidate pack (B-track, no Track A replace)."""

from __future__ import annotations

from scripts.build_mkm_inter_agent_health_signoff_candidate_v1 import build


def test_health_signoff_candidate_schema() -> None:
    doc = build()
    assert doc["does_not_replace_track_a_active"] is True
    assert doc["human_review_required"] is True
    assert doc["hypothesis_tier"] == "B"
    assert doc.get("cmp2_011_focus", {}).get("active_report_row") is not None
