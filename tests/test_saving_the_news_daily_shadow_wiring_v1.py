"""Saving the News Phase 3b daily shadow wiring (research_only)."""

from __future__ import annotations

import scripts.build_commander_telegram_advanced_briefing_v1 as adv
from scripts.build_saving_the_news_internal_roadmap_closure_v1 import build_closure


def test_hyper_personal_shadow_enabled_defaults_on(monkeypatch) -> None:
    monkeypatch.delenv("MKM_HYPER_PERSONAL_INTAKE_SHADOW", raising=False)
    assert adv.hyper_personal_shadow_enabled() is True


def test_hyper_personal_shadow_disabled_by_env(monkeypatch) -> None:
    monkeypatch.setenv("MKM_HYPER_PERSONAL_INTAKE_SHADOW", "0")
    assert adv.hyper_personal_shadow_enabled() is False


def test_internal_roadmap_closure_includes_phase3b() -> None:
    doc = build_closure()
    assert doc["schema"] == "saving_the_news_internal_roadmap_closure_v1"
    assert doc["lane"] == "research_only"
    assert "phase3b_hyper_personal_poc_status_v1" in doc["phases"]
    assert doc["promote_track_a_or_live"] is False
    assert doc["ready_for_external_send"] is False
    assert doc["news_hp_rt"]["interpretation"] == "research_only_delta"
