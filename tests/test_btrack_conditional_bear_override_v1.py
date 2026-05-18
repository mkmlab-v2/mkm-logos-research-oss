"""Tests for conditional bear override gate."""
from __future__ import annotations

from scripts.btrack_conditional_bear_override_v1 import apply_conditional_bear_override_v1


def test_cbo_applies_when_bull_price_last_neg() -> None:
    rules = {
        "conditional_bear_override": {
            "enabled": True,
            "when": {"price_score_min": 0.03, "weighted_min": 0.03},
            "action": "negate_weighted",
        }
    }
    lens = {
        "price": {"score": 0.2},
        "macro": {"score": 0.1},
    }
    w, direction, meta = apply_conditional_bear_override_v1(
        weighted=0.15,
        preliminary_direction="bull",
        lens_values=lens,
        price_meta={"last_daily_return": -0.01},
        margin=0.03,
        rules=rules,
    )
    assert meta["applied"] is True
    assert w < 0
    assert direction == "bear"


def test_cbo_skips_when_last_return_positive() -> None:
    rules = {"conditional_bear_override": {"enabled": True, "when": {"price_score_min": 0.03}}}
    w, direction, meta = apply_conditional_bear_override_v1(
        weighted=0.15,
        preliminary_direction="bull",
        lens_values={"price": {"score": 0.2}, "macro": {"score": 0.0}},
        price_meta={"last_daily_return": 0.01},
        margin=0.03,
        rules=rules,
    )
    assert meta["applied"] is False
    assert direction == "bull"
    assert w == 0.15
