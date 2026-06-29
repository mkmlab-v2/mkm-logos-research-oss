"""Tests for KOSPI weight counterfactual lib."""

from __future__ import annotations

from scripts.kospi_weight_counterfactual_lib_v1 import (
    WEIGHT_SCENARIOS,
    build_session_weight_counterfactual,
    replay_scenario,
    scenario_ids_for_panel,
)


def test_scenario_ids_default() -> None:
    ids = scenario_ids_for_panel({"enabled": True})
    assert "equal_weight_8ch" in ids
    assert "macro_off_session_half" in ids


def test_build_session_counterfactual_shape() -> None:
    cal_row = {
        "session_date": "2026-06-26",
        "session_mapping_target": "bull",
        "session_direction_score": 0.15,
        "momentum_direction": "bear",
    }
    doc = build_session_weight_counterfactual(
        session_date="2026-06-26",
        cal_row=cal_row,
        actual_direction="bear",
        active_direction="bull",
        scenario_ids=["active_v2_lens3_heavy", "equal_weight_8ch"],
        rules={"neutral_band": 0.06, "blend_policy_v2": {}},
    )
    assert doc["schema"] == "kospi_june2026_weight_counterfactual_v1"
    assert len(doc["scenarios"]) == 2
    names = {s["scenario"] for s in doc["scenarios"]}
    assert names == {"active_v2_lens3_heavy", "equal_weight_8ch"}
    assert "equal_weight_8ch" in WEIGHT_SCENARIOS


def test_bear_triple_align_boost_v2_rescues_2026_06_26() -> None:
    from pathlib import Path
    import json

    cal = json.loads(
        Path("reports/kospi_202606_daily_prophecy_calendar_v1.json").read_text(encoding="utf-8-sig")
    )
    cal_row = next(r for r in cal["rows"] if r["session_date"] == "2026-06-26")
    pred, _, _ = replay_scenario(
        cal_row,
        scenario_id="bear_triple_align_boost_v2",
        neutral_band=0.06,
        blend_policy={
            "directional_winner_min_weight": 0.28,
            "directional_margin_ratio": 1.12,
            "prefer_directional_over_neutral": True,
            "require_directional_plurality": True,
        },
    )
    assert pred == "bear"
