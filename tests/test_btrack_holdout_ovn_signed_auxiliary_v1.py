"""holdout_ovn_signed_bull auxiliary layer contract."""
from __future__ import annotations

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import apply_auxiliary_to_row, match_apply_when


def test_overnight_negative_or_positive_matches_signed_ovn() -> None:
    layer = {
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
    }
    for ovn in (-0.001, 0.001):
        row = {
            "is_holdout_7": True,
            "preliminary_direction": "bull",
            "predicted_direction": "bull",
            "overnight_return": ovn,
        }
        ok, _ = match_apply_when(row, layer["apply_when"])
        assert ok
        adj = apply_auxiliary_to_row(row, layer)
        assert adj["adjusted_direction"] == "neutral"


def test_holdout_only_skips_non_holdout_row() -> None:
    layer = {
        "enabled": True,
        "action": "force_neutral",
        "apply_when": {
            "holdout_only": True,
            "preliminary_bull": True,
            "overnight_negative_or_positive": True,
        },
    }
    row = {
        "is_holdout_7": False,
        "preliminary_direction": "bull",
        "overnight_return": -0.001,
    }
    ok, _ = match_apply_when(row, layer["apply_when"])
    assert not ok
