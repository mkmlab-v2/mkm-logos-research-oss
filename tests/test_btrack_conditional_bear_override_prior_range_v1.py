"""CBO prior_range_low gate checks."""
from __future__ import annotations

from scripts.btrack_conditional_bear_override_v1 import apply_conditional_bear_override_v1


def test_cbo_fires_when_ovn_and_prior_range_low() -> None:
    rules = {
        "conditional_bear_override": {
            "enabled": True,
            "when": {
                "price_score_min": 0.03,
                "weighted_min": 0.03,
                "overnight_negative": True,
                "prior_range_low": True,
                "prior_range_low_max": 0.25,
            },
            "action": "negate_weighted",
        }
    }
    w, direction, meta = apply_conditional_bear_override_v1(
        weighted=0.15,
        preliminary_direction="bull",
        lens_values={"price": {"score": 0.2, "confidence": 0.2}, "macro": {"score": 0.1, "confidence": 0.1}},
        price_meta={
            "last_daily_return": -0.01,
            "overnight_return": -0.02,
            "prior_range_position": 0.1,
        },
        margin=0.03,
        rules=rules,
    )
    assert meta.get("applied") is True
    assert direction == "bear"
    assert w < 0


def test_cbo_skips_when_prior_range_high() -> None:
    rules = {
        "conditional_bear_override": {
            "enabled": True,
            "when": {
                "price_score_min": 0.03,
                "weighted_min": 0.03,
                "overnight_negative": True,
                "prior_range_low": True,
                "prior_range_low_max": 0.25,
            },
            "action": "negate_weighted",
        }
    }
    _, direction, meta = apply_conditional_bear_override_v1(
        weighted=0.15,
        preliminary_direction="bull",
        lens_values={"price": {"score": 0.2, "confidence": 0.2}},
        price_meta={"overnight_return": -0.02, "prior_range_position": 0.8},
        margin=0.03,
        rules=rules,
    )
    assert meta.get("applied") is False
    assert direction == "bull"
