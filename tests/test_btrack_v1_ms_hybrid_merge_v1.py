"""Unit tests for v1+MS hybrid merge rules."""
from __future__ import annotations

from scripts.run_btrack_v1_ms_hybrid_parallel_v1 import (
    HYBRID_RULES,
    _merge_agree_only,
    _merge_ms_when_active_else_v1,
)


def test_ms_when_active_else_v1() -> None:
    assert _merge_ms_when_active_else_v1("bull", "bear") == "bear"
    assert _merge_ms_when_active_else_v1("bull", "neutral") == "bull"


def test_agree_only() -> None:
    assert _merge_agree_only("bull", "bull") == "bull"
    assert _merge_agree_only("bull", "bear") == "neutral"
    assert _merge_agree_only("neutral", "bear") == "neutral"


def test_rules_registered() -> None:
    assert "ms_when_active_else_v1" in HYBRID_RULES
    assert len(HYBRID_RULES) >= 5
