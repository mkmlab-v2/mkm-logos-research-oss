"""Phase 3 join — composite flow and join row shape."""
from __future__ import annotations

from scripts.join_btrack_phase3_leading_sensors_score_v1 import _composite_signed_flow
from scripts.run_btrack_phase3_leading_sensors_ablation_v1 import (
    _rows_for_profile,
    _sensor_confirms,
    _sensor_opposes,
)


def test_composite_signed_flow() -> None:
    by_date = {
        "2026-01-01": {
            "a": {"features": {"signed_flow_z": 0.2}},
            "b": {"features": {"signed_flow_z": -0.1}},
        }
    }
    v = _composite_signed_flow(by_date, "2026-01-01", ["a", "b"])
    assert v == 0.05


def test_shield_neutralizes_opposing_bull() -> None:
    rows = [
        {
            "eval_date": "2026-01-01",
            "instrument": "btc",
            "predicted_direction": "bull",
            "actual_direction": "bear",
            "leading_composite_signed_flow_z": -0.2,
        }
    ]
    shaped = _rows_for_profile(rows, "leading_shield_v1", threshold=0.05)
    assert shaped[0]["predicted_direction"] == "neutral"
    assert _sensor_opposes("bull", -0.2, threshold=0.05)


def test_confirm_filter_skips_disagree() -> None:
    rows = [
        {
            "eval_date": "2026-01-01",
            "instrument": "btc",
            "predicted_direction": "bull",
            "actual_direction": "bull",
            "leading_composite_signed_flow_z": 0.2,
        },
        {
            "eval_date": "2026-01-02",
            "instrument": "btc",
            "predicted_direction": "bull",
            "actual_direction": "bear",
            "leading_composite_signed_flow_z": -0.2,
        },
    ]
    shaped = _rows_for_profile(rows, "leading_confirm_active", threshold=0.05)
    assert len(shaped) == 1
    assert _sensor_confirms("bull", 0.2, threshold=0.05)
