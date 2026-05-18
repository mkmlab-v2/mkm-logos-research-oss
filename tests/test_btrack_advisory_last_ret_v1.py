"""Advisory rules: last_daily_return_negative + prior_range 0.35."""
from __future__ import annotations

from scripts.btrack_wrong_dir_auxiliary_layer_v1 import match_apply_when


def test_last_daily_return_negative_required() -> None:
    row = {
        "preliminary_direction": "bull",
        "predicted_direction": "bull",
        "overnight_return": -0.01,
        "prior_range_position": 0.2,
        "last_daily_return": 0.01,
        "lens_values": {"price": {"score": 0.05}},
    }
    aw = {
        "preliminary_bull": True,
        "overnight_negative": True,
        "prior_range_low": True,
        "prior_range_low_max": 0.35,
        "last_daily_return_negative": True,
    }
    ok, _ = match_apply_when(row, aw)
    assert ok is False

    row["last_daily_return"] = -0.02
    ok2, checks = match_apply_when(row, aw)
    assert ok2 is True
    assert checks["last_daily_return_negative"] is True


def test_last_daily_return_at_eval() -> None:
    from scripts.btrack_causal_ohlc_features_v1 import last_daily_return_at_eval

    closes = {"2026-04-01": 100.0, "2026-04-02": 98.0, "2026-04-03": 99.0}
    ret = last_daily_return_at_eval(closes, "2026-04-04")
    assert ret is not None
    # Last session before 04-04: 04-02 close 98 -> 04-03 close 99
    assert abs(ret - (99.0 - 98.0) / 98.0) < 1e-9
