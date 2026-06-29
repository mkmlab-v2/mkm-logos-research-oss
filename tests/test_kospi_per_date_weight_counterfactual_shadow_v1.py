"""Tests for per-date lens + weight counterfactual shadow."""

from __future__ import annotations

from pathlib import Path

import json

from scripts.kospi_lens_per_date_static_v1 import load_lens_jsonl_by_day
from scripts.kospi_weight_counterfactual_lib_v1 import (
    replay_scenario,
    replay_scenario_per_date,
    score_weight_rule_month_per_date,
)


def test_replay_scenario_per_date_bear_triple_2026_06_26_divergence() -> None:
    """Static snapshot rescues 6/26; per_date JSONL bull consensus blocks bear_triple."""
    cal = json.loads(
        Path("reports/kospi_202606_daily_prophecy_calendar_v1.json").read_text(encoding="utf-8-sig")
    )
    rules = json.loads(
        Path("data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8-sig")
    )
    cal_row = next(r for r in cal["rows"] if r["session_date"] == "2026-06-26")
    my_by, sa_by, _ = load_lens_jsonl_by_day(
        Path("data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"),
        Path("data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"),
    )
    bp = rules.get("blend_policy_v2") or {}
    nb = float(rules.get("neutral_band", 0.06))
    static_pred, _, _ = replay_scenario(
        cal_row,
        scenario_id="bear_triple_align_boost_v2",
        neutral_band=nb,
        blend_policy=bp,
    )
    per_pred, detail, _ = replay_scenario_per_date(
        cal_row,
        scenario_id="bear_triple_align_boost_v2",
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        neutral_band=nb,
        blend_policy=bp,
    )
    assert static_pred == "bear"
    assert per_pred == "bull"
    votes = detail.get("votes") or {}
    assert float(votes.get("bull") or 0) > float(votes.get("bear") or 0)


def test_score_weight_rule_month_per_date_shape() -> None:
    cal = json.loads(
        Path("reports/kospi_202606_daily_prophecy_calendar_v1.json").read_text(encoding="utf-8-sig")
    )
    ev = json.loads(
        Path("reports/kospi_june2026_daily_prophecy_eval_latest.json").read_text(encoding="utf-8-sig")
    )
    rules = json.loads(
        Path("data/commander/kospi_june2026_prophecy_evolution_v1.json").read_text(encoding="utf-8-sig")
    )
    my_by, sa_by, _ = load_lens_jsonl_by_day(
        Path("data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"),
        Path("data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"),
    )
    doc = score_weight_rule_month_per_date(
        calendar=cal,
        eval_doc=ev,
        scenario_id="active_v2_lens3_heavy",
        rules=rules,
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        as_of_kst="2026-06-26",
    )
    assert doc["type"] == "blend_weights_per_date_lenses"
    assert doc["n_scored"] >= 1
    assert "rule" in doc and "active" in doc
