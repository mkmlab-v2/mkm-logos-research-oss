"""Tests for export_kospi_composite_shadow_daily_drill_v1."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.export_kospi_composite_shadow_daily_drill_v1 import _classify_reason


def test_classify_reason_active_unchanged():
    assert (
        _classify_reason(
            active="neutral",
            bear_triple="bear",
            composite="neutral",
            unlock_candidate=True,
            allow_unlock=False,
        )
        == "active_unchanged"
    )


def test_classify_reason_bear_triple_default():
    assert (
        _classify_reason(
            active="bull",
            bear_triple="bear",
            composite="bear",
            unlock_candidate=False,
            allow_unlock=False,
        )
        == "bear_triple_default"
    )


def test_classify_reason_4ai_unlock():
    assert (
        _classify_reason(
            active="neutral",
            bear_triple="bear",
            composite="bull",
            unlock_candidate=True,
            allow_unlock=True,
        )
        == "4ai_unlock"
    )
