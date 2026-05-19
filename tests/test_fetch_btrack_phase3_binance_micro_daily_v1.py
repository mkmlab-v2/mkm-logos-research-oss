"""Binance micro fetch helpers."""
from __future__ import annotations

from scripts.fetch_btrack_phase3_binance_micro_daily_v1 import _z_score


def test_z_score_bounded() -> None:
    series = [0.0001, 0.0002, 0.00015, 0.00018, 0.00012, 0.00011, 0.00009, 0.00008]
    z = _z_score(series, 0.0005)
    assert -1.0 <= z <= 1.0
    assert z > 0
