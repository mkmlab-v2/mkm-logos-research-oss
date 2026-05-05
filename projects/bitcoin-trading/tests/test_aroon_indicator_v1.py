import pytest

from src.futures_engine.indicators.aroon import aroon_up_down


def test_aroon_up_at_new_high():
    highs = [1.0, 2.0, 10.0]
    lows = [1.0, 1.0, 1.0]
    up, down = aroon_up_down(highs, lows, period=3)
    assert up == pytest.approx(100.0)
    assert down == pytest.approx(100.0 / 3.0)


def test_aroon_requires_length():
    with pytest.raises(ValueError):
        aroon_up_down([1.0], [1.0], period=3)
