#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hero macro_news_shock -> kospi_direction neutral shadow gate [HYPO][research_only]."""

from __future__ import annotations

from typing import Any

from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome


DEFAULT_POLICY: dict[str, Any] = {
    "enabled": True,
    "status": "research_shadow",
    "shock_probability_min": 0.5,
    "require_shock_pred_binary": True,
    "only_when_active_bull": True,
    "require_foreign_flow_net_sell_pred": True,
    "shadow_direction": "neutral",
    "apply_to": "kospi_direction_only",
    "oos_forward_start": "2026-07-01",
    "auto_apply": False,
    "note_ko": "shock_pred + foreign 순매도 예측 + active bull 시 neutral shadow. Track A·live apply 금지.",
}


def resolve_policy(rules: dict[str, Any] | None) -> dict[str, Any]:
    raw = (rules or {}).get("hero_shock_gate_shadow_policy")
    if not isinstance(raw, dict):
        return dict(DEFAULT_POLICY)
    return {**DEFAULT_POLICY, **raw}


def _foreign_flow_net_sell_pred(foreign_pred: dict[str, Any] | None) -> bool:
    if not isinstance(foreign_pred, dict):
        return False
    if foreign_pred.get("predicted_binary") is False:
        return True
    try:
        p = float(foreign_pred.get("probability_0_1") or 0.5)
    except (TypeError, ValueError):
        p = 0.5
    return p < 0.5


def shock_gate_applies(
    shock_pred: dict[str, Any] | None,
    policy: dict[str, Any],
    *,
    active_direction: str | None = None,
    foreign_flow_pred: dict[str, Any] | None = None,
) -> bool:
    if not policy.get("enabled", True):
        return False
    shock_pred = shock_pred if isinstance(shock_pred, dict) else {}
    try:
        p = float(shock_pred.get("probability_0_1") or 0.0)
    except (TypeError, ValueError):
        p = 0.0
    pred_b = bool(shock_pred.get("predicted_binary"))
    min_p = float(policy.get("shock_probability_min", 0.5))
    shock_ok = (pred_b or p >= min_p) if bool(policy.get("require_shock_pred_binary", True)) else p >= min_p
    if not shock_ok:
        return False
    if bool(policy.get("only_when_active_bull", False)):
        if str(active_direction or "").strip().lower() != "bull":
            return False
    if bool(policy.get("require_foreign_flow_net_sell_pred", False)):
        if not _foreign_flow_net_sell_pred(foreign_flow_pred):
            return False
    return True


def apply_shock_gate_shadow(
    active_direction: str,
    shock_pred: dict[str, Any] | None,
    *,
    policy: dict[str, Any] | None = None,
    foreign_flow_pred: dict[str, Any] | None = None,
) -> tuple[str, bool, dict[str, Any]]:
    """Return (shadow_direction, gate_applied, meta)."""
    pol = resolve_policy(policy)
    active = str(active_direction or "neutral").strip().lower()
    if not shock_gate_applies(
        shock_pred,
        pol,
        active_direction=active,
        foreign_flow_pred=foreign_flow_pred,
    ):
        return active, False, {"gate_applied": False, "active_direction": active}
    shadow = str(pol.get("shadow_direction") or "neutral").strip().lower()
    if shadow not in ("bull", "bear", "neutral"):
        shadow = "neutral"
    return (
        shadow,
        True,
        {
            "gate_applied": True,
            "gate_id": "hero_shock_gate_shadow_v1",
            "active_direction": active,
            "shadow_direction": shadow,
            "shock_probability_0_1": (shock_pred or {}).get("probability_0_1"),
            "shock_predicted_binary": (shock_pred or {}).get("predicted_binary"),
            "foreign_flow_net_sell_pred": _foreign_flow_net_sell_pred(foreign_flow_pred),
        },
    )


def _metrics_from_outcomes(outcomes: list[str]) -> dict[str, Any]:
    if not outcomes:
        return {
            "n_scored": 0,
            "hit": 0,
            "fail": 0,
            "neutral_draw": 0,
            "directional_hit_rate": None,
            "soft_hit_rate": None,
        }
    hit = sum(1 for o in outcomes if o == "HIT")
    fail = sum(1 for o in outcomes if o == "FAIL")
    neutral = sum(1 for o in outcomes if o == "NEUTRAL_DRAW")
    n = len(outcomes)
    directional = hit + fail
    return {
        "n_scored": n,
        "hit": hit,
        "fail": fail,
        "neutral_draw": neutral,
        "directional_hit_rate": round(hit / directional, 4) if directional else None,
        "soft_hit_rate": round((hit + 0.5 * neutral) / n, 4),
    }


def score_shadow_day(
    *,
    session_date: str,
    active_direction: str,
    actual_direction: str,
    shock_pred: dict[str, Any] | None,
    policy: dict[str, Any] | None = None,
    foreign_flow_pred: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shadow_dir, applied, meta = apply_shock_gate_shadow(
        active_direction,
        shock_pred,
        policy=policy,
        foreign_flow_pred=foreign_flow_pred,
    )
    active_out = _outcome(active_direction, actual_direction)
    shadow_out = _outcome(shadow_dir, actual_direction)
    softened = active_out == "FAIL" and shadow_out == "NEUTRAL_DRAW"
    rescued = active_out == "FAIL" and shadow_out == "HIT"
    worsened = active_out == "HIT" and shadow_out in ("FAIL", "NEUTRAL_DRAW")
    return {
        "session_date": session_date,
        "actual_direction": actual_direction,
        "active_direction": active_direction,
        "shadow_direction": shadow_dir,
        "active_outcome": active_out,
        "shadow_outcome": shadow_out,
        "gate_applied": applied,
        "softened_active_fail": softened,
        "rescued_active_fail": rescued,
        "worsened_active_hit": worsened,
        "shock_pred": {
            "probability_0_1": (shock_pred or {}).get("probability_0_1"),
            "predicted_binary": (shock_pred or {}).get("predicted_binary"),
        },
        "foreign_flow_pred": {
            "probability_0_1": (foreign_flow_pred or {}).get("probability_0_1"),
            "predicted_binary": (foreign_flow_pred or {}).get("predicted_binary"),
        },
        "gate_meta": meta,
    }


def aggregate_shadow_days(days: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [d for d in days if d.get("actual_direction")]
    active_outcomes = [str(d.get("active_outcome") or "") for d in scored]
    shadow_outcomes = [str(d.get("shadow_outcome") or "") for d in scored]
    gated = [d for d in scored if d.get("gate_applied")]
    return {
        "n_days": len(days),
        "n_scored": len(scored),
        "n_gate_applied": len(gated),
        "active": _metrics_from_outcomes(active_outcomes),
        "shadow": _metrics_from_outcomes(shadow_outcomes),
        "n_softened_active_fail": sum(1 for d in scored if d.get("softened_active_fail")),
        "n_rescued_active_fail": sum(1 for d in scored if d.get("rescued_active_fail")),
        "n_worsened_active_hit": sum(1 for d in scored if d.get("worsened_active_hit")),
        "shadow_minus_active_soft_pp": round(
            (_metrics_from_outcomes(shadow_outcomes).get("soft_hit_rate") or 0.0)
            - (_metrics_from_outcomes(active_outcomes).get("soft_hit_rate") or 0.0),
            4,
        )
        if scored
        else None,
    }
