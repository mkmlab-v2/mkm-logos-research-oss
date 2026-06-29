"""Tests for parallel shadow bundle composite + fail rescue logic."""

from __future__ import annotations

from scripts.build_kospi_june2026_parallel_shadow_bundle_v1 import fail_rescue_direction
from scripts.kospi_composite_shadow_lib_v1 import composite_bear_conditional as composite_direction


def test_composite_unlock_allowed_uses_coordinator() -> None:
    assert (
        composite_direction(
            v2="neutral",
            bear_triple="bear",
            coord_raw="bull",
            unlock_candidate=True,
            cond_allow=True,
        )
        == "bull"
    )


def test_composite_unlock_blocked_stays_v2() -> None:
    assert (
        composite_direction(
            v2="neutral",
            bear_triple="bear",
            coord_raw="bull",
            unlock_candidate=True,
            cond_allow=False,
        )
        == "neutral"
    )


def test_composite_default_bear_triple() -> None:
    assert (
        composite_direction(
            v2="bull",
            bear_triple="bear",
            coord_raw="bull",
            unlock_candidate=False,
            cond_allow=True,
        )
        == "bear"
    )


def test_fail_rescue_stress_bull_to_bear_triple() -> None:
    assert (
        fail_rescue_direction(
            active="bull",
            bear_triple="bear",
            shock_applied=True,
            suppressed_bears=0,
            foreign_sell=False,
        )
        == "bear"
    )


def test_fail_rescue_calm_keeps_active() -> None:
    assert (
        fail_rescue_direction(
            active="bull",
            bear_triple="bear",
            shock_applied=False,
            suppressed_bears=0,
            foreign_sell=False,
        )
        == "bull"
    )
