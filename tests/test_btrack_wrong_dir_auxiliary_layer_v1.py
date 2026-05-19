"""Auxiliary layer matching and apply."""
from __future__ import annotations

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_to_row, match_apply_when


def test_match_ovn_and_prior_range_low() -> None:
    row = {
        "predicted_direction": "bull",
        "preliminary_direction": "bull",
        "overnight_return": -0.02,
        "prior_range_position": 0.1,
        "is_holdout_7": True,
        "lens_values": {"price": {"score": 0.2}},
    }
    aw = {
        "preliminary_bull": True,
        "overnight_negative": True,
        "prior_range_low": True,
        "prior_range_low_max": 0.25,
    }
    ok, _ = match_apply_when(row, aw)
    assert ok is True


def test_force_neutral_on_match() -> None:
    row = {
        "predicted_direction": "bull",
        "preliminary_direction": "bull",
        "overnight_return": -0.01,
        "prior_range_position": 0.2,
        "confidence": 0.25,
        "lens_values": {"price": {"score": 0.15}},
    }
    layer = {
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "preliminary_bull": True,
            "overnight_negative": True,
            "prior_range_low": True,
            "prior_range_low_max": 0.25,
        },
    }
    out = apply_auxiliary_to_row(row, layer)
    assert out["auxiliary_applied"] is True
    assert out["adjusted_direction"] == "neutral"
