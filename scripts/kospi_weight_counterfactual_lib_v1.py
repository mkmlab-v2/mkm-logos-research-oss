#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weight counterfactual scenarios for KOSPI direction replay [HYPO][research_only]."""

from __future__ import annotations

from typing import Any

from scripts.build_kospi_june2026_channel_input_audit_v1 import (  # noqa: E402
    _momentum_from_row,
    _replay_row,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome
from scripts.kospi_june2026_multilens_blend_v1 import load_ensemble_kospi_per_date, load_static_lenses

ACTIVE_WEIGHTS: dict[str, float] = {
    "session_myeongni": 0.3,
    "myeongni_independent": 0.22,
    "sasang": 0.24,
    "logos_non_gating": 0.0,
    "macro": 0.24,
    "field_regime": 0.0,
    "momentum_overlay": 0.0,
    "ensemble_kospi_causal": 0.0,
}

WEIGHT_SCENARIOS: dict[str, dict[str, Any]] = {
    "active_v2_lens3_heavy": {
        "type": "blend_weights",
        "weights": dict(ACTIVE_WEIGHTS),
        "note_ko": "현재 apply arm — baseline",
    },
    "equal_weight_8ch": {
        "type": "blend_weights",
        "weights": {k: 0.125 for k in ACTIVE_WEIGHTS},
        "note_ko": "8채널 균등 — 6/26 bear HIT rescue 후보",
    },
    "macro_off_session_half": {
        "type": "blend_weights",
        "weights": {
            "session_myeongni": 0.15,
            "myeongni_independent": 0.22,
            "sasang": 0.24,
            "logos_non_gating": 0.08,
            "macro": 0.0,
            "field_regime": 0.12,
            "momentum_overlay": 0.12,
            "ensemble_kospi_causal": 0.1,
        },
        "note_ko": "macro=0 · session 0.15 — 6/26 bear HIT rescue 후보",
    },
    "shadow_field_momentum": {
        "type": "blend_weights",
        "weights": {
            "session_myeongni": 0.2206,
            "myeongni_independent": 0.1618,
            "sasang": 0.1765,
            "logos_non_gating": 0.0,
            "macro": 0.1765,
            "field_regime": 0.1324,
            "momentum_overlay": 0.1324,
            "ensemble_kospi_causal": 0.0,
        },
        "note_ko": "field+momentum shadow 후보",
    },
    "bear_triple_align_boost_v2": {
        "type": "blend_weights",
        "weights": {
            "session_myeongni": 0.21,
            "myeongni_independent": 0.15,
            "sasang": 0.15,
            "macro": 0.09,
            "logos_non_gating": 0.12,
            "field_regime": 0.15,
            "momentum_overlay": 0.2,
            "ensemble_kospi_causal": 0.0,
        },
        "note_ko": "HD grid — logos+field+momentum bear 채널 가중(6/26 rescue) · June forward shadow",
    },
}


def scenario_ids_for_panel(policy: dict[str, Any] | None) -> list[str]:
    pol = policy if isinstance(policy, dict) else {}
    if pol.get("enabled") is False:
        return []
    raw = pol.get("rule_ids") or pol.get("weight_scenario_ids")
    if isinstance(raw, list) and raw:
        return [str(x) for x in raw]
    return ["equal_weight_8ch", "macro_off_session_half", "bear_triple_align_boost_v2"]


def replay_scenario(
    cal_row: dict[str, Any],
    *,
    scenario_id: str,
    static_lenses: dict[str, Any] | None = None,
    ensemble_by_date: dict[str, dict[str, Any]] | None = None,
    neutral_band: float = 0.06,
    blend_policy: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, float]]:
    spec = WEIGHT_SCENARIOS.get(scenario_id)
    if not spec:
        raise KeyError(f"unknown scenario: {scenario_id}")
    weights = spec["weights"]
    dk = str(cal_row.get("session_date"))
    static = static_lenses if static_lenses is not None else load_static_lenses()
    ens = ensemble_by_date
    if ens is None:
        ens = load_ensemble_kospi_per_date([dk])
    pred, detail = _replay_row(
        cal_row,
        static_lenses=static,
        ensemble_by_date=ens,
        weights=weights,
        neutral_band=neutral_band,
        blend_policy=blend_policy or {},
    )
    return pred, detail, weights


def replay_scenario_per_date(
    cal_row: dict[str, Any],
    *,
    scenario_id: str,
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    ensemble_by_date: dict[str, dict[str, Any]] | None = None,
    baseline_static: dict[str, Any] | None = None,
    neutral_band: float = 0.06,
    blend_policy: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, float]]:
    from scripts.kospi_lens_per_date_static_v1 import static_lenses_for_eval_date

    dk = str(cal_row.get("session_date"))[:10]
    per_static = static_lenses_for_eval_date(
        dk,
        sasang_by_day=sasang_by_day,
        myeongni_by_day=myeongni_by_day,
        baseline=baseline_static or load_static_lenses(),
    )
    return replay_scenario(
        cal_row,
        scenario_id=scenario_id,
        static_lenses=per_static,
        ensemble_by_date=ensemble_by_date,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )


def build_session_weight_counterfactual(
    *,
    session_date: str,
    cal_row: dict[str, Any],
    actual_direction: str,
    active_direction: str,
    scenario_ids: list[str] | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rules = rules or {}
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    ids = scenario_ids or list(WEIGHT_SCENARIOS.keys())
    dk = session_date[:10]
    static = load_static_lenses()
    ens = load_ensemble_kospi_per_date([dk])

    scenarios: list[dict[str, Any]] = []
    rescues: list[str] = []
    softens: list[str] = []
    active_out = _outcome(active_direction, actual_direction)

    for sid in ids:
        pred, detail, weights = replay_scenario(
            cal_row,
            scenario_id=sid,
            static_lenses=static,
            ensemble_by_date=ens,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        oc = _outcome(pred, actual_direction)
        row = {
            "scenario": sid,
            "predicted_direction": pred,
            "outcome": oc,
            "blended_score": detail.get("blended_score"),
            "votes": detail.get("votes"),
            "winner_resolution": detail.get("winner_resolution"),
            "weights": weights,
            "rescues_active_fail": active_out == "FAIL" and oc == "HIT",
            "softens_active_fail": active_out == "FAIL" and oc == "NEUTRAL_DRAW",
        }
        scenarios.append(row)
        if row["rescues_active_fail"]:
            rescues.append(sid)
        if row["softens_active_fail"]:
            softens.append(sid)

    suppressed = []
    mom = _momentum_from_row(cal_row)
    if mom == "bear":
        for ch in ("logos_non_gating", "field_regime", "momentum_overlay"):
            if ACTIVE_WEIGHTS.get(ch, 0) == 0:
                suppressed.append(ch)

    return {
        "schema": "kospi_june2026_weight_counterfactual_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "session_date": dk,
        "actual_direction": actual_direction,
        "active_direction": active_direction,
        "channel_inputs": {
            "session": str(cal_row.get("session_mapping_target") or ""),
            "momentum": mom,
            "suppressed_bear": suppressed,
        },
        "scenarios": scenarios,
        "rescues_active_fail": rescues,
        "softens_active_fail": softens,
    }


def score_weight_rule_month(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    scenario_id: str,
    rules: dict[str, Any],
    as_of_kst: str | None = None,
) -> dict[str, Any]:
    cal_by = {
        str(r.get("session_date") or "")[:10]: r
        for r in (calendar.get("rows") or [])
        if isinstance(r, dict) and r.get("session_date")
    }
    eval_rows = [r for r in (eval_doc.get("rows") or []) if isinstance(r, dict)]
    if as_of_kst:
        eval_rows = [r for r in eval_rows if str(r.get("session_date") or "") <= as_of_kst[:10]]

    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    trading_days = list(cal_by.keys())
    static = load_static_lenses()
    ens = load_ensemble_kospi_per_date(trading_days)

    days: list[dict[str, Any]] = []
    rule_outcomes: list[str] = []
    active_outcomes: list[str] = []

    for er in eval_rows:
        dk = str(er.get("session_date") or "")[:10]
        cal_row = cal_by.get(dk)
        if not cal_row:
            continue
        actual = str(er.get("actual_direction") or "neutral")
        active = str(er.get("predicted_direction") or "neutral")
        pred, detail, weights = replay_scenario(
            cal_row,
            scenario_id=scenario_id,
            static_lenses=static,
            ensemble_by_date=ens,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        active_oc = _outcome(active, actual)
        rule_oc = _outcome(pred, actual)
        active_outcomes.append(active_oc)
        rule_outcomes.append(rule_oc)
        days.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "active_direction": active,
                "rule_direction": pred,
                "active_outcome": active_oc,
                "rule_outcome": rule_oc,
                "rescued_active_fail": active_oc == "FAIL" and rule_oc == "HIT",
                "softened_active_fail": active_oc == "FAIL" and rule_oc == "NEUTRAL_DRAW",
                "votes": detail.get("votes"),
                "weights": weights,
            }
        )

    from scripts.kospi_hero_shock_gate_shadow_lib_v1 import _metrics_from_outcomes

    active_m = _metrics_from_outcomes(active_outcomes)
    rule_m = _metrics_from_outcomes(rule_outcomes)
    return {
        "rule_id": scenario_id,
        "type": "blend_weights",
        "n_scored": len(days),
        "active": active_m,
        "rule": rule_m,
        "rule_minus_active_soft_pp": round(
            (rule_m.get("soft_hit_rate") or 0.0) - (active_m.get("soft_hit_rate") or 0.0),
            4,
        )
        if days
        else None,
        "n_rescued_active_fail": sum(1 for d in days if d.get("rescued_active_fail")),
        "n_softened_active_fail": sum(1 for d in days if d.get("softened_active_fail")),
        "days": days,
    }


def score_weight_rule_month_per_date(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    scenario_id: str,
    rules: dict[str, Any],
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    as_of_kst: str | None = None,
) -> dict[str, Any]:
    cal_by = {
        str(r.get("session_date") or "")[:10]: r
        for r in (calendar.get("rows") or [])
        if isinstance(r, dict) and r.get("session_date")
    }
    eval_rows = [r for r in (eval_doc.get("rows") or []) if isinstance(r, dict)]
    if as_of_kst:
        eval_rows = [r for r in eval_rows if str(r.get("session_date") or "") <= as_of_kst[:10]]

    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    trading_days = list(cal_by.keys())
    baseline_static = load_static_lenses()
    ens = load_ensemble_kospi_per_date(trading_days)

    days: list[dict[str, Any]] = []
    rule_outcomes: list[str] = []
    active_outcomes: list[str] = []

    for er in eval_rows:
        dk = str(er.get("session_date") or "")[:10]
        cal_row = cal_by.get(dk)
        if not cal_row:
            continue
        actual = str(er.get("actual_direction") or "neutral")
        active = str(er.get("predicted_direction") or "neutral")
        pred, detail, weights = replay_scenario_per_date(
            cal_row,
            scenario_id=scenario_id,
            myeongni_by_day=myeongni_by_day,
            sasang_by_day=sasang_by_day,
            ensemble_by_date=ens,
            baseline_static=baseline_static,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        active_oc = _outcome(active, actual)
        rule_oc = _outcome(pred, actual)
        active_outcomes.append(active_oc)
        rule_outcomes.append(rule_oc)
        days.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "active_direction": active,
                "rule_direction": pred,
                "active_outcome": active_oc,
                "rule_outcome": rule_oc,
                "rescued_active_fail": active_oc == "FAIL" and rule_oc == "HIT",
                "softened_active_fail": active_oc == "FAIL" and rule_oc == "NEUTRAL_DRAW",
                "votes": detail.get("votes"),
                "weights": weights,
            }
        )

    from scripts.kospi_hero_shock_gate_shadow_lib_v1 import _metrics_from_outcomes

    active_m = _metrics_from_outcomes(active_outcomes)
    rule_m = _metrics_from_outcomes(rule_outcomes)
    return {
        "rule_id": scenario_id,
        "type": "blend_weights_per_date_lenses",
        "n_scored": len(days),
        "active": active_m,
        "rule": rule_m,
        "rule_minus_active_soft_pp": round(
            (rule_m.get("soft_hit_rate") or 0.0) - (active_m.get("soft_hit_rate") or 0.0),
            4,
        )
        if days
        else None,
        "n_rescued_active_fail": sum(1 for d in days if d.get("rescued_active_fail")),
        "n_softened_active_fail": sum(1 for d in days if d.get("softened_active_fail")),
        "days": days,
    }
