"""Hero shock_gate shadow PoC tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shock_gate_applies_on_binary_pred():
    from scripts.kospi_hero_shock_gate_shadow_lib_v1 import apply_shock_gate_shadow

    shadow, applied, _ = apply_shock_gate_shadow(
        "bull",
        {"probability_0_1": 0.6, "predicted_binary": True},
        foreign_flow_pred={"probability_0_1": 0.47, "predicted_binary": False},
    )
    assert applied is True
    assert shadow == "neutral"


def test_shock_gate_noop_when_shock_low():
    from scripts.kospi_hero_shock_gate_shadow_lib_v1 import apply_shock_gate_shadow

    shadow, applied, _ = apply_shock_gate_shadow(
        "bull",
        {"probability_0_1": 0.28, "predicted_binary": False},
    )
    assert applied is False
    assert shadow == "bull"


def test_score_shadow_day_0626_softens_fail():
    from scripts.kospi_hero_shock_gate_shadow_lib_v1 import score_shadow_day

    row = score_shadow_day(
        session_date="2026-06-26",
        active_direction="bull",
        actual_direction="bear",
        shock_pred={"probability_0_1": 0.6, "predicted_binary": True},
        foreign_flow_pred={"probability_0_1": 0.47, "predicted_binary": False},
    )
    assert row["active_outcome"] == "FAIL"
    assert row["shadow_outcome"] == "NEUTRAL_DRAW"
    assert row["softened_active_fail"] is True


def test_shock_gate_skips_bull_hit_without_foreign_sell():
    from scripts.kospi_hero_shock_gate_shadow_lib_v1 import score_shadow_day

    row = score_shadow_day(
        session_date="2026-06-09",
        active_direction="bull",
        actual_direction="bull",
        shock_pred={"probability_0_1": 0.6, "predicted_binary": True},
        foreign_flow_pred={"probability_0_1": 0.55, "predicted_binary": True},
    )
    assert row["gate_applied"] is False
    assert row["shadow_outcome"] == "HIT"


def test_build_shadow_panel_smoke():
    from scripts.build_kospi_hero_shock_gate_shadow_v1 import build_shadow_panel

    kospi_eval = json.loads(
        (ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json").read_text(encoding="utf-8-sig")
    )
    hero_cal = json.loads(
        (ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    rules = json.loads(
        (ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8-sig")
    )
    doc = build_shadow_panel(
        kospi_eval=kospi_eval,
        hero_cal=hero_cal,
        rules=rules,
        as_of_kst="2026-06-26",
        year_month="2026-06",
    )
    assert doc["schema"] == "kospi_hero_shock_gate_shadow_v1"
    assert doc["aggregate"]["n_scored"] >= 1
    day = next(d for d in doc["days"] if d["session_date"] == "2026-06-26")
    assert day["gate_applied"] is True
    assert day["softened_active_fail"] is True
