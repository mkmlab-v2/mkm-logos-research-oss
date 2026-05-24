#!/usr/bin/env python3
"""Conditional ensemble bear override when price bull conflicts with last-day return (B-track)."""
from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _sgn_to_dir(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def apply_conditional_bear_override_v1(
    *,
    weighted: float,
    preliminary_direction: str,
    lens_values: dict[str, Any],
    price_meta: dict[str, Any],
    margin: float,
    rules: dict[str, Any] | None,
) -> tuple[float, str, dict[str, Any]]:
    """Research-only gate: flip bullish ensemble call when last causal day was negative."""
    rules = rules or {}
    cfg = rules.get("conditional_bear_override")
    if not isinstance(cfg, dict) or not cfg.get("enabled"):
        return weighted, preliminary_direction, {"applied": False, "enabled": False}

    when = cfg.get("when") if isinstance(cfg.get("when"), dict) else {}
    price_min = _safe_float(when.get("price_score_min"), 0.03)
    weighted_min = _safe_float(when.get("weighted_min"), margin)
    require_macro_bull = bool(when.get("require_macro_bull", False))
    macro_min = _safe_float(when.get("macro_score_min"), 0.0)

    price_blob = lens_values.get("price") if isinstance(lens_values.get("price"), dict) else {}
    macro_blob = lens_values.get("macro") if isinstance(lens_values.get("macro"), dict) else {}
    price_score = _safe_float(price_blob.get("score"), 0.0)
    macro_score = _safe_float(macro_blob.get("score"), 0.0)
    last_ret = _safe_float(price_meta.get("last_daily_return"), 0.0)
    overnight = price_meta.get("overnight_return")
    require_overnight_neg = bool(when.get("overnight_negative", False))
    overnight_neg = overnight is not None and _safe_float(overnight, 0.0) < 0
    pr_pos = price_meta.get("prior_range_position")
    pr_f = _safe_float(pr_pos, 0.5) if pr_pos is not None else None
    require_pr_low = bool(when.get("prior_range_low", False))
    pr_low_max = _safe_float(when.get("prior_range_low_max"), 0.25)
    pr_low_ok = (not require_pr_low) or (pr_f is not None and pr_f < pr_low_max)
    require_pr_high = bool(when.get("prior_range_high", False))
    pr_high_min = _safe_float(when.get("prior_range_high_min"), 0.75)
    pr_high_ok = (not require_pr_high) or (pr_f is not None and pr_f > pr_high_min)

    checks = {
        "preliminary_bull": preliminary_direction == "bull",
        "price_lens_bull": price_score > price_min,
        "last_return_negative": last_ret < 0,
        "overnight_negative": (not require_overnight_neg) or overnight_neg,
        "prior_range_low": pr_low_ok,
        "prior_range_high": pr_high_ok,
        "weighted_bull": weighted > weighted_min,
        "macro_bull": (not require_macro_bull) or (macro_score > macro_min),
    }
    if not all(checks.values()):
        return weighted, preliminary_direction, {
            "applied": False,
            "enabled": True,
            "checks": checks,
            "reason": "conditions_not_met",
        }

    action = str(cfg.get("action") or "negate_weighted").strip().lower()
    new_weighted = weighted
    if action == "negate_weighted":
        new_weighted = -abs(weighted)
    elif action == "halve_and_negate":
        new_weighted = -abs(weighted) * 0.5
    elif action == "force_bear":
        new_weighted = -max(abs(weighted), margin + 1e-6)
    else:
        new_weighted = -abs(weighted)

    new_prelim = "neutral" if abs(new_weighted) < margin else _sgn_to_dir(new_weighted)
    return new_weighted, new_prelim, {
        "applied": True,
        "enabled": True,
        "action": action,
        "checks": checks,
        "weighted_before": round(weighted, 6),
        "weighted_after": round(new_weighted, 6),
        "preliminary_before": preliminary_direction,
        "preliminary_after": new_prelim,
    }
