#!/usr/bin/env python3
"""compression_profile economy | fidelity | literal → evaluate_report kwargs (Fact-Lock).

Bench SSOT (do not mix runs):
- economy: 41658 lexicon ultra-default — **49.1% / Jaccard 0.873** (MS Policy A); frozen MS paste 47.5%/0.890 = 41775 path
- fidelity: comp_atom01 bridge_on (32.2% / 0.967) — not the uplift AB (35.3% / 0.932)
- literal: MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1 (~23.6% / 0.975)
"""

from __future__ import annotations

from typing import Any, Literal

from scripts.compression_token_api_stub import _decision_selected_profile

CompressionProfile = Literal["economy", "fidelity", "literal"]

# Literal caps aligned with scripts/run_ultra_compression_default.py (Track B literal).
_LITERAL_STRATEGY = "C"
_LITERAL_INTENSITY = "high"
_LITERAL_GENERAL_MAX = 0.28
_LITERAL_SENSITIVE_MAX = 0.26
_LITERAL_HANGUL_MAX = 0.30

PROFILE_BENCH_SSOT: dict[CompressionProfile, dict[str, Any]] = {
    "economy": {
        "bench_artifact": "reports/constitution/btrack_pilot/comp_atom01_ab_summary_v1.json",
        "metrics_control_row": "metrics_control",
        "apply_gematria_4d_bridge_policy": False,
        "headline_global_token_saving_rate": 0.49085794655414905,
        "headline_jaccard": 0.8727418293565741,
    },
    "fidelity": {
        "bench_artifact": "reports/constitution/btrack_pilot/comp_atom01_ab_summary_v1.json",
        "metrics_control_row": "metrics_bridge_on",
        "apply_gematria_4d_bridge_policy": True,
        "headline_global_token_saving_rate": 0.32208157524613223,
        "headline_jaccard": 0.9667631571859513,
    },
    "literal": {
        "bench_artifact": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json",
        "metrics_control_row": "compression_metrics",
        "apply_gematria_4d_bridge_policy": False,
        "headline_global_token_saving_rate": 0.23628691983122363,
        "headline_jaccard": 0.975,
    },
}


def profile_meta(profile: CompressionProfile) -> dict[str, Any]:
    row = PROFILE_BENCH_SSOT[profile]
    return {
        "compression_profile": profile,
        "bench_ssot_artifact": row["bench_artifact"],
        "bench_metrics_row": row["metrics_control_row"],
        "apply_gematria_4d_bridge_policy": row["apply_gematria_4d_bridge_policy"],
        "headline_bench_global_token_saving_rate": row["headline_global_token_saving_rate"],
        "headline_bench_jaccard": row["headline_jaccard"],
        "integrity_note": "must_keep_sensitive_integrity_gate_not_semantic_perfect_reconstruction",
        "fail_comp_004": "planning_S_L_K_M_axes_not_runtime_gematria_to_4d_bridge_axes",
    }


def _decision_strategy_intensity() -> tuple[str, str, float | None, float | None, float | None]:
    selected = _decision_selected_profile()
    strategy = str(selected.get("strategy", "A"))
    intensity = str(selected.get("intensity", "extreme"))
    general_cap = selected.get("general_max_saving_rate")
    sensitive_cap = selected.get("sensitive_max_saving_rate")
    hangul_cap = selected.get("hangul_max_saving_rate")
    return (
        strategy if strategy in {"A", "B", "C"} else "A",
        intensity if intensity in {"high", "ultra", "extreme"} else "extreme",
        float(general_cap) if general_cap is not None else None,
        float(sensitive_cap) if sensitive_cap is not None else None,
        float(hangul_cap) if hangul_cap is not None else None,
    )


def profile_evaluate_report_kwargs_v2(
    profile: CompressionProfile,
    *,
    graph_wire_selective_bridge: bool = False,
) -> dict[str, Any]:
    """v2 API kwargs; economy+wire uses bench-aligned _base_eval_kwargs (COMP-ATOM-05)."""
    if profile == "economy" and graph_wire_selective_bridge:
        from scripts.comp_graphrag_philosophy_compression_sweep_v1 import (  # noqa: WPS433
            _base_eval_kwargs,
        )

        kw = _base_eval_kwargs()
        kw["apply_gematria_4d_bridge_policy"] = False
        kw["bench_aligned"] = "comp_atom05_full_v2_wire_selective"
        return kw
    kw = profile_evaluate_report_kwargs(profile)
    if graph_wire_selective_bridge and profile == "fidelity":
        kw = dict(kw)
        kw["bench_aligned"] = "fidelity_global_bridge_wire_redundant"
    return kw


def profile_evaluate_report_kwargs(profile: CompressionProfile) -> dict[str, Any]:
    """Kwargs for evaluate_report (excluding per-request doc fields)."""
    strategy, intensity, general_cap, sensitive_cap, hangul_cap = _decision_strategy_intensity()
    bridge = PROFILE_BENCH_SSOT[profile]["apply_gematria_4d_bridge_policy"]
    if profile == "literal":
        strategy, intensity = _LITERAL_STRATEGY, _LITERAL_INTENSITY
        general_cap, sensitive_cap, hangul_cap = (
            _LITERAL_GENERAL_MAX,
            _LITERAL_SENSITIVE_MAX,
            _LITERAL_HANGUL_MAX,
        )
    return {
        "strategy": strategy,
        "intensity": intensity,
        "general_max_saving_rate": general_cap,
        "sensitive_max_saving_rate": sensitive_cap,
        "hangul_max_saving_rate": hangul_cap,
        "use_domain_router": True,
        "use_master_codebook_lexicon_v1": True,
        "include_gematria_metadata": bool(bridge),
        "include_gematria_4d_bridge": bool(bridge),
        "include_cee_core": bool(bridge),
        "apply_gematria_4d_bridge_policy": bool(bridge),
    }
