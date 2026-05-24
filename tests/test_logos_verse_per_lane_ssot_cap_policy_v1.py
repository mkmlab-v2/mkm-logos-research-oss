"""Tests for logos verse per-lane SSOT cap policy loader."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_load_policy_and_overrides() -> None:
    from scripts.logos_verse_per_lane_ssot_cap_policy_v1 import (
        eval_cap_overrides,
        load_policy,
        policy_allows_pool_mode,
    )

    policy = load_policy(ROOT / "reports/logos_verse_per_lane_ssot_cap_policy_v1_latest.json")
    assert policy_allows_pool_mode(policy, "homogeneous_logos_verse")
    assert not policy_allows_pool_mode(policy, "mixed_matrix")
    ov = eval_cap_overrides(policy)
    assert ov["general_max_saving_rate"] == 0.15
    assert ov["domain_relaxed_max_saving_overrides"] == {}
