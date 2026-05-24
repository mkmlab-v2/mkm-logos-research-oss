#!/usr/bin/env python3
"""Macro-bear / overnight-negative price-lens dampen on ensemble weighted score (B-track)."""
from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def apply_regime_conditional_price_dampen_v1(
    *,
    lens_values: dict[str, Any],
    weighted_raw: float,
    weights: dict[str, float],
    price_meta: dict[str, Any],
    rules: dict[str, Any] | None,
) -> tuple[float, dict[str, Any], dict[str, Any]]:
    rules = rules or {}
    cfg = rules.get("regime_conditional_price_dampen")
    if not isinstance(cfg, dict) or not cfg.get("enabled"):
        return weighted_raw, lens_values, {"applied": False, "enabled": False}

    price_blob = lens_values.get("price") if isinstance(lens_values.get("price"), dict) else {}
    macro_blob = lens_values.get("macro") if isinstance(lens_values.get("macro"), dict) else {}
    price_score = _safe_float(price_blob.get("score"), 0.0)
    macro_score = _safe_float(macro_blob.get("score"), 0.0)
    overnight = price_meta.get("overnight_return")
    overnight_f = _safe_float(overnight, 0.0) if overnight is not None else None

    macro_thresh = _safe_float(cfg.get("macro_bear_threshold"), 0.0)
    macro_mult = _safe_float(cfg.get("macro_bear_price_mult"), 0.5)
    ovn_mult = _safe_float(cfg.get("overnight_neg_price_mult"), 0.5)

    mult = 1.0
    triggers: list[str] = []
    if bool(cfg.get("dampen_when_macro_bear")) and macro_score < -macro_thresh:
        mult *= macro_mult
        triggers.append("macro_bear")
    if bool(cfg.get("dampen_when_overnight_negative")) and overnight_f is not None and overnight_f < 0:
        mult *= ovn_mult
        triggers.append("overnight_negative")
    vol_high_thresh = _safe_float(cfg.get("vol_high_realized_5d"), 0.03)
    vol_mult = _safe_float(cfg.get("vol_high_price_mult"), 0.6)
    rv = price_meta.get("realized_vol_5d")
    rv_f = _safe_float(rv, 0.0) if rv is not None else None
    if bool(cfg.get("dampen_when_vol_regime_high")) and rv_f is not None and rv_f >= vol_high_thresh:
        mult *= vol_mult
        triggers.append("vol_regime_high")

    if mult >= 1.0 or not triggers:
        return weighted_raw, lens_values, {"applied": False, "enabled": True, "triggers": triggers}

    w_price = _safe_float(weights.get("price"), 0.0)
    price_contrib = w_price * price_score
    new_weighted = weighted_raw - price_contrib + price_contrib * mult
    new_lens = dict(lens_values)
    new_price = dict(price_blob)
    new_price["score"] = max(-1.0, min(1.0, price_score * mult))
    new_lens["price"] = new_price
    return new_weighted, new_lens, {
        "applied": True,
        "enabled": True,
        "triggers": triggers,
        "price_multiplier": round(mult, 6),
        "weighted_before": round(weighted_raw, 6),
        "weighted_after": round(new_weighted, 6),
    }
