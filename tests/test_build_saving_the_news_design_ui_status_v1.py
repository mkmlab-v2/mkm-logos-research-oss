"""Design UI status builder smoke."""

from __future__ import annotations

from scripts.build_saving_the_news_design_ui_status_v1 import build_status


def test_design_ui_status_schema_and_lane() -> None:
    doc = build_status()
    assert doc["schema"] == "saving_the_news_design_ui_status_v1"
    assert doc["lane"] == "research_only"
    assert doc["ready_for_external_send"] is False
    crit = doc["exit_criteria"]
    assert crit["shadow_observation_only"] is True
    assert crit["cms_publish_allowed"] is False
    assert "D1_mkmlife_deck_artifact" in crit
    assert "D9_jemaai_matrix_hp_footnote" in crit
    if all(crit.get(k) for k in crit if k not in ("shadow_observation_only", "cms_publish_allowed")):
        assert doc["status"] == "DESIGN_UI_POC_COMPLETE"
