"""Small-sample guardrails for prophecy-only OOS."""
from __future__ import annotations

from scripts.kospi_field_band_small_sample_guardrails_v1 import (
    CONSECUTIVE_OOS_PASS_REQUIRED,
    HOLDOUT_N_DISCUSSION_MIN,
    TOTAL_SCORED_HEADLINE_MIN,
    build_small_sample_guardrails,
    consecutive_oos_passes,
)


def test_guardrails_block_small_n_not_discussion_eligible():
    oos = {
        "prophecy_only_oos_ready": True,
        "holdout_pooled": {"stack_union": {"n_scored": 25, "band_hit_rate": 0.68}},
        "n_scored_total": 34,
        "delta_stack_minus_base_holdout": 0.28,
    }
    g = build_small_sample_guardrails(oos)
    assert g["promotion_candidate_research"] is True
    assert g["track_a_discussion_eligible"] is False
    assert f"holdout_n_lt_{HOLDOUT_N_DISCUSSION_MIN}" in g["blockers"]
    assert f"total_scored_n_lt_{TOTAL_SCORED_HEADLINE_MIN}" in g["blockers"]


def test_guardrails_large_n_still_needs_consecutive_passes(tmp_path):
    log = tmp_path / "oos.jsonl"
    log.write_text(
        '{"prophecy_only_oos_ready": true, "delta_stack_minus_base_holdout": 0.05}\n',
        encoding="utf-8",
    )
    oos = {
        "prophecy_only_oos_ready": True,
        "holdout_pooled": {"stack_union": {"n_scored": 35, "band_hit_rate": 0.7}},
        "n_scored_total": 45,
        "delta_stack_minus_base_holdout": 0.05,
    }
    g = build_small_sample_guardrails(oos, log_path=log)
    assert consecutive_oos_passes(log) == 1
    assert g["track_a_discussion_eligible"] is False
    assert f"consecutive_oos_pass_lt_{CONSECUTIVE_OOS_PASS_REQUIRED}" in g["blockers"]
