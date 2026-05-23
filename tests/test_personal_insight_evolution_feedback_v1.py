"""personal_insight_evolution_feedback_v1 validation and aggregation smoke tests."""

from __future__ import annotations

from pathlib import Path

from scripts.personal_insight_evolution_feedback_v1 import (
    build_evolution_candidates,
    summarize_feedback,
    validate_event,
)

ROOT = Path(__file__).resolve().parents[1]


def _sample_event(**overrides: object) -> dict:
    row = {
        "schema": "personal_insight_evolution_feedback_v1",
        "event_id": "piev1_test_001",
        "ts_utc": "2026-05-20T12:00:00Z",
        "product_lane": "personadiary",
        "surface": "daily_guide",
        "helpful": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "preview_only": True,
    }
    row.update(overrides)
    return row


def test_validate_event_ok() -> None:
    assert validate_event(_sample_event()) == []


def test_validate_event_rejects_bad_lane() -> None:
    assert "product_lane_invalid" in validate_event(_sample_event(product_lane="invalid"))


def test_summarize_empty_dir() -> None:
    summary = summarize_feedback(window_days=7, base_dir=ROOT / "reports/tmp_piev1_test_empty")
    assert summary["schema"] == "personal_insight_evolution_feedback_summary_v1"
    assert summary["total_events"] == 0


def test_build_candidates_from_summary() -> None:
    summary = {
        "schema": "personal_insight_evolution_feedback_summary_v1",
        "by_product_lane": {
            "personadiary": {
                "real_user_events": 5,
                "helpful_rate": 0.4,
            }
        },
    }
    out = build_evolution_candidates(summary)
    assert out["schema"] == "personal_insight_evolution_candidates_v1"
    assert out["mode"] == "proposal_only_no_auto_apply"
    assert any(c["product_lane"] == "personadiary" for c in out["candidates"])
