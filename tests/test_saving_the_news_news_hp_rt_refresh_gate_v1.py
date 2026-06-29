"""NEWS-HP-RT refresh gate (research_only)."""

from __future__ import annotations

from scripts.check_saving_the_news_news_hp_rt_refresh_gate_v1 import evaluate_gate


def test_gate_holds_before_not_before() -> None:
    doc = evaluate_gate(not_before="2099-01-01", force=False)
    assert doc["calendar_gate_open"] is False
    assert doc["refresh_allowed"] is False
    assert doc["decision_label"] == "HOLD_WATCH"


def test_gate_force_overrides_calendar() -> None:
    doc = evaluate_gate(not_before="2099-01-01", force=True)
    assert doc["refresh_allowed"] is True
    assert doc["decision_label"] == "GO_REFRESH"


def test_gate_open_after_not_before_with_interval() -> None:
    doc = evaluate_gate(not_before="2000-01-01", min_hours_since_bench=0, force=False)
    assert doc["calendar_gate_open"] is True
    assert doc["refresh_recommended"] is True
    assert doc["refresh_allowed"] is True
