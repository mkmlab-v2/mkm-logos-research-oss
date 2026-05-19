"""Unit tests for price lens calibration helpers."""
from __future__ import annotations

from scripts.btrack_price_lens_calibration_v1 import compute_price_lens_from_returns


def test_bear_dampen_on_positive_score_and_negative_last_day() -> None:
    returns = [0.01, 0.008, 0.006, 0.004, -0.02]
    score_plain, _, _ = compute_price_lens_from_returns(returns)
    score_damp, _, meta = compute_price_lens_from_returns(
        returns, bear_dampen_if_last_day_negative=0.5
    )
    assert score_plain > 0
    assert meta["bear_dampen_applied"] is True
    assert score_damp < score_plain


def test_last_day_blend_pulls_toward_recent() -> None:
    returns = [0.01, 0.01, 0.01, 0.01, -0.03]
    _, _, m0 = compute_price_lens_from_returns(returns, last_day_blend=0.0)
    score_hi, _, _ = compute_price_lens_from_returns(returns, last_day_blend=0.5)
    assert score_hi < compute_price_lens_from_returns(returns)[0]


def test_flip_to_bear_when_last_negative() -> None:
    returns = [0.01, 0.008, 0.006, 0.004, -0.02]
    score_before, _, _ = compute_price_lens_from_returns(returns)
    score_after, _, meta = compute_price_lens_from_returns(
        returns, flip_to_bear_when_last_negative=True
    )
    assert score_before > 0
    assert meta["flip_last_applied"] is True
    assert score_after < 0


def test_invert_price_score_sign() -> None:
    returns = [0.01, 0.01, 0.01]
    plain, _, _ = compute_price_lens_from_returns(returns)
    inv, _, meta = compute_price_lens_from_returns(returns, invert_price_score_sign=True)
    assert meta["invert_applied"] is True
    assert inv == -plain
