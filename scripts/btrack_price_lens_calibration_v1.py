#!/usr/bin/env python3
"""Price lens score helpers for B-track bear-day calibration (research_only)."""
from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_price_lens_from_returns(
    returns: list[float],
    *,
    return_scale_divisor: float = 0.02,
    last_day_blend: float = 0.0,
    bear_dampen_if_last_day_negative: float = 1.0,
    invert_price_score_sign: bool = False,
    flip_to_bear_when_avg_negative: bool = False,
    flip_to_bear_when_last_negative: bool = False,
    overnight_return: float | None = None,
    overnight_blend: float = 0.0,
    prior_range_position: float | None = None,
    prior_range_blend: float = 0.0,
    flip_to_bear_when_prior_range_low: bool = False,
    prior_range_low_threshold: float = 0.25,
) -> tuple[float, float, dict[str, Any]]:
    """Map causal daily returns to bounded direction score + confidence."""
    if not returns:
        return 0.0, 0.0, {"reason": "no_returns"}
    scale = max(1e-6, _safe_float(return_scale_divisor, 0.02))
    blend = max(0.0, min(1.0, _safe_float(last_day_blend, 0.0)))
    dampen = max(0.0, min(1.0, _safe_float(bear_dampen_if_last_day_negative, 1.0)))
    avg_ret = sum(returns) / len(returns)
    last_ret = returns[-1]
    blended_ret = (1.0 - blend) * avg_ret + blend * last_ret if blend > 0 else avg_ret
    ovn_blend = max(0.0, min(1.0, _safe_float(overnight_blend, 0.0)))
    overnight_ret = overnight_return
    if ovn_blend > 0 and overnight_ret is not None:
        blended_ret = (1.0 - ovn_blend) * blended_ret + ovn_blend * float(overnight_ret)
    pr_blend = max(0.0, min(1.0, _safe_float(prior_range_blend, 0.0)))
    pr_pos = prior_range_position
    pr_low_thresh = _safe_float(prior_range_low_threshold, 0.25)
    if pr_blend > 0 and pr_pos is not None:
        pr_signal = 2.0 * (float(pr_pos) - 0.5) * scale
        blended_ret = (1.0 - pr_blend) * blended_ret + pr_blend * pr_signal
    direction_score = max(-1.0, min(1.0, blended_ret / scale))
    flip_pr_low_applied = False
    if (
        flip_to_bear_when_prior_range_low
        and pr_pos is not None
        and float(pr_pos) < pr_low_thresh
        and direction_score > 0
    ):
        direction_score = -abs(direction_score)
        flip_pr_low_applied = True
    bear_dampen_applied = False
    if dampen < 1.0 and last_ret < 0 and direction_score > 0:
        direction_score *= dampen
        bear_dampen_applied = True
    flip_last_applied = False
    if flip_to_bear_when_last_negative and last_ret < 0 and direction_score > 0:
        direction_score = -abs(direction_score)
        flip_last_applied = True
    flip_avg_applied = False
    if flip_to_bear_when_avg_negative and avg_ret < 0 and direction_score > 0:
        direction_score = -abs(direction_score)
        flip_avg_applied = True
    invert_applied = False
    if invert_price_score_sign:
        direction_score = -direction_score
        invert_applied = True
    direction_score = max(-1.0, min(1.0, direction_score))
    confidence = max(0.0, min(1.0, abs(direction_score)))
    return direction_score, confidence, {
        "avg_daily_return": avg_ret,
        "last_daily_return": last_ret,
        "blended_return": blended_ret,
        "return_scale_divisor": scale,
        "last_day_blend": blend,
        "bear_dampen_if_last_day_negative": dampen,
        "bear_dampen_applied": bear_dampen_applied,
        "flip_to_bear_when_last_negative": flip_to_bear_when_last_negative,
        "flip_last_applied": flip_last_applied,
        "flip_to_bear_when_avg_negative": flip_to_bear_when_avg_negative,
        "flip_avg_applied": flip_avg_applied,
        "invert_price_score_sign": invert_price_score_sign,
        "invert_applied": invert_applied,
        "overnight_return": overnight_ret,
        "overnight_blend": ovn_blend,
        "prior_range_position": pr_pos,
        "prior_range_blend": pr_blend,
        "flip_to_bear_when_prior_range_low": flip_to_bear_when_prior_range_low,
        "flip_pr_low_applied": flip_pr_low_applied,
    }


def calibration_from_rules(rules: dict[str, Any] | None) -> dict[str, Any]:
    rules = rules or {}
    cal = rules.get("price_lens_calibration")
    return dict(cal) if isinstance(cal, dict) else {}
