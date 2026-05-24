#!/usr/bin/env python3
"""[HYPO] Auxiliary post-ensemble layer — downgrade/neutral cap without touching ensemble JSON."""
from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool_match(required: bool, actual: bool) -> bool:
    return (not required) or actual


def match_apply_when(row: dict[str, Any], apply_when: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Match causal + ensemble fields on a per-date BTC row."""
    aw = apply_when or {}
    pred = str(row.get("predicted_direction") or "").lower()
    prelim = str(row.get("preliminary_direction") or pred).lower()
    price_score = _safe_float((row.get("lens_values") or {}).get("price", {}).get("score"), 0.0)
    if not isinstance(row.get("lens_values"), dict):
        price_score = _safe_float(row.get("price_lens_score"), price_score)
    last_ret = row.get("last_daily_return")
    last_ret_f = _safe_float(last_ret, 0.0) if last_ret is not None else None

    ovn = row.get("overnight_return")
    ovn_f = _safe_float(ovn, 0.0) if ovn is not None else None
    prp = row.get("prior_range_position")
    prp_f = _safe_float(prp, 0.5) if prp is not None else None
    rv = row.get("realized_vol_5d")
    rv_f = _safe_float(rv, 0.0) if rv is not None else None

    pr_hi_min = _safe_float(aw.get("prior_range_high_min"), 0.75)
    ovn_neg = ovn_f is not None and ovn_f < 0
    ovn_pos = ovn_f is not None and ovn_f > 0
    pr_hi = prp_f is not None and prp_f >= pr_hi_min

    checks = {
        "preliminary_bull": (not aw.get("preliminary_bull")) or prelim == "bull",
        "predicted_bull": (not aw.get("predicted_bull")) or pred == "bull",
        "overnight_negative": (not aw.get("overnight_negative")) or ovn_neg,
        "overnight_positive": (not aw.get("overnight_positive")) or ovn_pos,
        "overnight_negative_or_positive": (not aw.get("overnight_negative_or_positive"))
        or (ovn_f is not None and ovn_f != 0),
        "overnight_negative_or_prior_range_high": (
            not aw.get("overnight_negative_or_prior_range_high")
        )
        or (ovn_neg or pr_hi),
        "prior_range_high": (not aw.get("prior_range_high")) or pr_hi,
        "prior_range_low": (not aw.get("prior_range_low"))
        or (prp_f is not None and prp_f < _safe_float(aw.get("prior_range_low_max"), 0.25)),
        "vol_regime_high": (not aw.get("vol_regime_high"))
        or (rv_f is not None and rv_f >= _safe_float(aw.get("vol_high_min"), 0.03)),
        "price_score_min": (not aw.get("price_score_min"))
        or price_score >= _safe_float(aw.get("price_score_min"), 0.03),
        "last_daily_return_negative": (not aw.get("last_daily_return_negative"))
        or (last_ret_f is not None and last_ret_f < 0),
        "is_wrong_direction_holdout": (not aw.get("holdout_only"))
        or bool(row.get("is_holdout_7")),
        "holdout_excluded": (not aw.get("holdout_exclude"))
        or (not bool(row.get("is_holdout_7"))),
    }
    return all(checks.values()), checks


def apply_auxiliary_to_row(
    row: dict[str, Any],
    layer: dict[str, Any],
) -> dict[str, Any]:
    """Return copy of row with optional adjusted_direction / advisory flags."""
    out = dict(row)
    if not layer.get("enabled", True):
        out["auxiliary_applied"] = False
        out["auxiliary_action"] = "noop"
        return out

    apply_when = layer.get("apply_when") if isinstance(layer.get("apply_when"), dict) else {}
    matched, checks = match_apply_when(row, apply_when)
    out["auxiliary_checks"] = checks
    if not matched:
        out["auxiliary_applied"] = False
        out["auxiliary_action"] = "skipped"
        out["adjusted_direction"] = out.get("predicted_direction")
        return out

    action = str(layer.get("action") or "force_neutral").strip().lower()
    pred = str(out.get("predicted_direction") or "neutral").lower()
    adjusted = pred
    if action == "force_neutral":
        adjusted = "neutral"
    elif action == "force_bear":
        adjusted = "bear"
    elif action == "cap_confidence":
        cap = _safe_float(layer.get("max_confidence"), 0.15)
        try:
            conf = float(out.get("confidence") or 0)
        except (TypeError, ValueError):
            conf = 0.0
        if conf > cap:
            adjusted = "neutral"
    elif action == "advisory_only":
        adjusted = pred
    else:
        adjusted = "neutral"

    out["auxiliary_applied"] = True
    out["auxiliary_action"] = action
    out["adjusted_direction"] = adjusted
    if action == "advisory_only":
        out["advisory_bear_trap"] = True
    return out


def apply_auxiliary_per_date_doc(
    per_date_doc: dict[str, Any],
    layer: dict[str, Any],
    *,
    instrument: str = "btc",
) -> dict[str, Any]:
    inst = instrument.strip().lower()
    new_rows: list[dict[str, Any]] = []
    for r in per_date_doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != inst:
            new_rows.append(r)
            continue
        adj = apply_auxiliary_to_row(r, layer)
        nr = dict(r)
        nr["predicted_direction"] = adj.get("adjusted_direction", r.get("predicted_direction"))
        nr["auxiliary_applied"] = adj.get("auxiliary_applied", False)
        nr["auxiliary_action"] = adj.get("auxiliary_action")
        if adj.get("advisory_bear_trap"):
            nr["advisory_bear_trap"] = True
        new_rows.append(nr)
    out = dict(per_date_doc)
    out["rows"] = new_rows
    out["auxiliary_layer"] = layer
    return out
