"""Unit tests for RFC F2/F3 causal OHLC features."""
from __future__ import annotations

from scripts.btrack_causal_ohlc_features_v1 import (
    actual_direction_at_eval,
    prior_range_position_at_eval,
    realized_vol_5d_at_eval,
    vol_regime_high,
)


def test_prior_range_position_mid_open() -> None:
    ohlc = {
        "2026-04-01": {"open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0},
        "2026-04-02": {"open": 100.0, "high": 120.0, "low": 80.0, "close": 100.0},
    }
    pos = prior_range_position_at_eval(ohlc, "2026-04-02")
    assert pos is not None
    assert 0.49 < pos < 0.51


def test_realized_vol_5d_positive() -> None:
    closes = {f"2026-04-{d:02d}": 100.0 + d for d in range(1, 12)}
    vol = realized_vol_5d_at_eval(closes, "2026-04-12", window=5)
    assert vol is not None
    assert vol >= 0.0


def test_actual_direction_bear_on_down_day() -> None:
    closes = {"2026-04-01": 100.0, "2026-04-02": 95.0}
    assert actual_direction_at_eval(closes, "2026-04-02", neutral_bps=5.0) == "bear"


def test_vol_regime_high_threshold() -> None:
    assert vol_regime_high(0.04, threshold=0.03) is True
    assert vol_regime_high(0.01, threshold=0.03) is False
