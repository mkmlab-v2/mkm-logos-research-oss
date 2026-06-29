"""Tests for kospi_composite_shadow_lib_v1."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.kospi_composite_shadow_lib_v1 import composite_active_hold, composite_bear_conditional


def test_bear_conditional_fallback_to_bear_triple():
    assert composite_bear_conditional(
        v2="bull", bear_triple="bear", coord_raw="bull", unlock_candidate=False, cond_allow=False
    ) == "bear"


def test_active_hold_keeps_v2_on_non_unlock():
    assert composite_active_hold(
        v2="bull", bear_triple="bear", coord_raw="bull", unlock_candidate=False, cond_allow=False
    ) == "bull"


def test_unlock_when_allowed():
    assert composite_bear_conditional(
        v2="neutral", bear_triple="bear", coord_raw="bull", unlock_candidate=True, cond_allow=True
    ) == "bull"
