# -*- coding: utf-8 -*-
"""Ops dynamical bench — ty_sparsity ↔ geumhwa_index linkage spec v1 [HYPO · B-track]."""

from __future__ import annotations

from typing import Any

from scripts.sasang_byeongjeung_symptom_weights_v1 import build_symptom_weights_v1

SCHEMA_ID = "ops_dynamical_ty_geumhwa_link_v1"
VERSION = "1.0.0"

FORMULA_ID = "geumhwa_index = K * (1 - M) * earth_mediation"
EXECUTION_THRESHOLD = 0.5

# Pedagogical TY-sparse boundary band on Ops K/M plane (not clinical prevalence).
BOUNDARY_K_MAX = 0.25
BOUNDARY_M_MIN = 0.35
BOUNDARY_M_MAX = 0.65
BOUNDARY_GH_MIN = 0.08
BOUNDARY_GH_MAX = 0.22


def earth_mediation_from_ops(*, solo_ok: bool | None, reddit_ok: bool | None) -> float:
    """Symbolic cleanup / governance proxy for earth mediation factor."""
    if solo_ok is True and reddit_ok is True:
        return 0.9
    if solo_ok is True or reddit_ok is True:
        return 0.75
    if solo_ok is False or reddit_ok is False:
        return 0.6
    return 0.7


def compute_geumhwa_index(*, k: float, m: float, earth_mediation: float) -> float:
    return round(max(0.0, min(1.0, k * (1.0 - m) * earth_mediation)), 4)


def build_ty_geumhwa_link_v1(
    *,
    slkm: dict[str, float],
    stress_score: float,
    stage: str,
    solo_ok: bool | None = None,
    reddit_ok: bool | None = None,
) -> dict[str, Any]:
    """Deterministic linkage block for ops_dynamical_bench_v1."""
    k = float(slkm.get("K", 0.0))
    m = float(slkm.get("M", 0.0))
    earth = earth_mediation_from_ops(solo_ok=solo_ok, reddit_ok=reddit_ok)
    geumhwa = compute_geumhwa_index(k=k, m=m, earth_mediation=earth)

    ty_ref = build_symptom_weights_v1()["ty_sparsity"]
    boost = float(ty_ref.get("risk_weight_boost") or 1.0)

    boundary_regime = (
        k <= BOUNDARY_K_MAX
        and BOUNDARY_M_MIN <= m <= BOUNDARY_M_MAX
        and BOUNDARY_GH_MIN <= geumhwa <= BOUNDARY_GH_MAX
        and geumhwa < EXECUTION_THRESHOLD
    )
    execution_mode = geumhwa > EXECUTION_THRESHOLD

    if execution_mode:
        regime_label = "execution"
    elif boundary_regime:
        regime_label = "boundary_sparse_ty_analog"
    elif stage in ("stress", "crisis"):
        regime_label = "stress_transition"
    else:
        regime_label = "calm_watch"

    uncertainty_multiplier = round(boost if boundary_regime else 1.0, 4)

    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "research_only": True,
        "hypothesis_class": "HYPO",
        "auto_trigger_forbidden": True,
        "formula_id": FORMULA_ID,
        "inputs": {
            "K": round(k, 4),
            "M": round(m, 4),
            "earth_mediation": earth,
            "stress_score": round(stress_score, 4),
            "ops_stage": stage,
        },
        "geumhwa_index": geumhwa,
        "execution_mode": execution_mode,
        "execution_threshold": EXECUTION_THRESHOLD,
        "ty_sparsity_ref": {
            "source": "scripts/sasang_byeongjeung_symptom_weights_v1.py",
            "cohort_pct_range": list(ty_ref.get("cohort_pct_range") or []),
            "risk_weight_boost": boost,
            "koges_excluded_in_literature": ty_ref.get("koges_excluded_in_literature"),
        },
        "boundary_regime": boundary_regime,
        "boundary_bands": {
            "K_max": BOUNDARY_K_MAX,
            "M_range": [BOUNDARY_M_MIN, BOUNDARY_M_MAX],
            "geumhwa_range": [BOUNDARY_GH_MIN, BOUNDARY_GH_MAX],
        },
        "regime_label": regime_label,
        "effective_uncertainty_multiplier": uncertainty_multiplier,
        "reading_ko": (
            "[HYPO] TY 희소성 ↔ 금화교역 경계 레짐 은유 — Ops K(게이트 잔여)·M(자원 압박) 평면에서만 읽습니다. "
            "임상 체질·실매매·send_gate 자동 개방 금지."
        ),
        "anchors": [
            "docs/research/FOUR_LENS_YINYANG_REGULARIZATION_V1.md",
            "docs/research/four_forces_sasang_biophysical/OPS_DYNAMICAL_PHASE_A_MAPPING_V1.md",
        ],
    }
