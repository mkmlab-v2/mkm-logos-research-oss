"""Phase 4 dual-arch status builder smoke."""

from __future__ import annotations

from scripts.build_saving_the_news_phase4_dual_arch_status_v1 import build_status


def test_phase4_dual_arch_status_complete_when_fixture_present() -> None:
    doc = build_status()
    assert doc["schema"] == "saving_the_news_phase4_dual_arch_status_v1"
    assert doc["lane"] == "research_only"
    assert doc["ready_for_external_send"] is False
    crit = doc["exit_criteria"]
    assert crit["P4-S1_section11_fixture"] is True
    assert crit["P4-S5_loss_four_axes"] is True
    assert doc["status"] == "POC_COMPLETE"
