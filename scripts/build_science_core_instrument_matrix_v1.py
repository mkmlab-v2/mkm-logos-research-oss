#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build Science Core instrument × layer matrix SSOT from governance bundle [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_GOV = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
DEFAULT_ATTACH = ROOT / "docs/final/artifacts/prophecy_lens_combo_science_core_attach_gate_v1_latest.json"
DEFAULT_COND = ROOT / "docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json"
DEFAULT_PROPHECY_SENS = ROOT / "docs/final/artifacts/science_core_prophecy_combo_sensitivity_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/science_core_instrument_matrix_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_instrument_matrix_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _slim_conditional_research(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    kospi = (doc.get("instrument_slices") or {}).get("kospi") or {}
    btc = (doc.get("instrument_slices") or {}).get("btc") or {}
    k_hor = kospi.get("holdout_horizon") or {}
    b_hor = btc.get("holdout_horizon") or {}
    return {
        "schema": doc.get("schema"),
        "generated_at_utc": doc.get("generated_at_utc"),
        "horizon_conditional_attach": doc.get("horizon_conditional_attach"),
        "btc_divergence": doc.get("btc_divergence"),
        "triple_blend_vs_fixed_combo": doc.get("triple_blend_vs_fixed_combo"),
        "kospi": {
            "horizon_attach_split_recommended": k_hor.get("horizon_attach_split_recommended"),
            "uplift_gap_short_minus_mid_pp": k_hor.get("uplift_gap_short_minus_mid_pp"),
            "shock_subset_sasang_uplift_pp": (
                (kospi.get("shock_subset_short_1d") or {}).get("science_plus_sasang") or {}
            ).get("uplift_vs_science_pp"),
            "calm_subset_sasang_uplift_pp": (
                (kospi.get("calm_subset_short_1d") or {}).get("science_plus_sasang") or {}
            ).get("uplift_vs_science_pp"),
        },
        "btc": {
            "shock_subset_sasang_uplift_pp": (
                (btc.get("shock_subset_short_1d") or {}).get("science_plus_sasang") or {}
            ).get("uplift_vs_science_pp"),
            "calm_subset_sasang_uplift_pp": (
                (btc.get("calm_subset_short_1d") or {}).get("science_plus_sasang") or {}
            ).get("uplift_vs_science_pp"),
            "short_1d_uplift_pp": (b_hor.get("short_1d") or {}).get("uplift_vs_science_pp"),
        },
        "final_action": doc.get("final_action"),
    }


def build_matrix(
    *,
    governance: dict[str, Any],
    attach_gate: dict[str, Any] | None,
    conditional_research: dict[str, Any] | None = None,
    prophecy_sensitivity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    window = governance.get("window") or {}
    holdout = governance.get("holdout") or {}
    humanist = governance.get("humanist_combo_holdout") or {}
    btc_aux = governance.get("btc_holdout_auxiliary") or {}
    parity = governance.get("instrument_parity_summary") or {}
    composite = governance.get("composite_attach") or {}
    promo = governance.get("promotion_gate") or {}
    pnl = governance.get("pnl_economic_significance") or {}
    pnl_hold = (pnl.get("holdout") or {}) if isinstance(pnl, dict) else {}
    wf = governance.get("walkforward") or {}

    kospi_short = (humanist.get("short_1d_soft") or {}) if isinstance(humanist, dict) else {}
    btc_short = (btc_aux.get("short_1d_soft") or {}) if isinstance(btc_aux, dict) else {}

    science_k = kospi_short.get("science_core")
    sasang_k = kospi_short.get("science_plus_sasang")
    uplift_k = holdout.get("kospi_holdout_uplift_soft")
    if uplift_k is None and science_k is not None and sasang_k is not None:
        uplift_k = round(float(sasang_k) - float(science_k), 4)

    science_b = btc_short.get("science_core")
    sasang_b = btc_short.get("science_plus_sasang")
    uplift_b = btc_aux.get("science_plus_sasang_uplift_vs_science_short_1d")

    attach_recommended = bool(composite.get("composite_attach_recommended"))
    recommended_lane = composite.get("recommended_lane")
    cond_slim = _slim_conditional_research(conditional_research)

    prophecy_slice: dict[str, Any] = {
        "task_type": "prophecy_combo_backtest",
        "role": "governance_gated_research_attach",
        "composite_attach_required": True,
        "attach_gate_present": attach_gate is not None,
        "combo_backtest_ran": bool((attach_gate or {}).get("combo_backtest_ran")),
        "recommended_lane": (attach_gate or {}).get("recommended_lane") or recommended_lane,
        "ssot_artifacts": [
            "docs/final/artifacts/prophecy_lens_combo_backtest_science_core_v1_latest.json",
            "docs/final/artifacts/prophecy_lens_combo_science_core_attach_gate_v1_latest.json",
            "docs/final/artifacts/science_core_prophecy_combo_sensitivity_v1_latest.json",
        ],
        "final_action": "RUN_ATTACH_IF_COMPOSITE_OK" if attach_recommended else "SKIP_ATTACH",
        "track_a_live_auto_merge": False,
    }
    if prophecy_sensitivity:
        prophecy_slice["fee_sensitivity"] = {
            "robust_positive_return_up_to_20bps": prophecy_sensitivity.get(
                "robust_positive_return_up_to_20bps"
            ),
            "baseline_recommended_lane_metrics": prophecy_sensitivity.get("baseline_recommended_lane_metrics"),
            "headline_claim_allowed": prophecy_sensitivity.get("headline_claim_allowed", False),
        }

    compression_slice: dict[str, Any] = {
        "task_type": "compression_track_a",
        "role": "out_of_scope_for_science_core_matrix",
        "ssot_policy": "docs/final/COMPRESSION_SLA_POLICY_V1.md",
        "ssot_bench": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        "final_action": "DO_NOT_MERGE_PROPHECY_OR_SCIENCE_KPI",
        "note_ko": "압축 Track A KPI와 Science/예언 soft hit·attach는 headline 합선 금지.",
    }

    kospi_slice: dict[str, Any] = {
        "instrument": "kospi",
        "role": "primary_attach",
        "field_id": "regime_science_core_v1_evaluation",
        "evaluation_window": window,
        "holdout_n": holdout.get("kospi_holdout_n") or humanist.get("n_eval_dates"),
        "science_quant": {
            "science_core_short_1d_soft": science_k,
            "horizon_eval_short_1d_soft": (
                ((governance.get("horizon_eval") or {}).get("kospi") or {}).get("science_core_summary") or {}
            ).get("short_1d_soft"),
        },
        "lens_overlay": {
            "sasang_role_ko": "단기 시장 심리(market sasang) 가산",
            "science_plus_sasang_short_1d_soft": sasang_k,
            "uplift_vs_science_short_1d_pp": uplift_k,
            "science_plus_myeongni_short_1d_soft": kospi_short.get("science_plus_myeongni"),
            "triple_short_1d_soft": kospi_short.get("science_plus_sasang_myeongni"),
            "triple_beats_sasang_on_holdout": humanist.get("triple_beats_sasang_on_holdout"),
            "attach_eligible_combos": [
                r.get("lens_id")
                for r in (humanist.get("attach_eligible_short_1d_ranking") or [])
                if isinstance(r, dict)
            ],
        },
        "pnl_holdout_sim": {
            "science_core_total_return": ((pnl_hold.get("science_core") or {}) if isinstance(pnl_hold, dict) else {}).get(
                "total_return"
            ),
            "science_plus_sasang_total_return": (
                (pnl_hold.get("science_plus_sasang") or {}) if isinstance(pnl_hold, dict) else {}
            ).get("total_return"),
            "science_plus_sasang_delta_vs_science": (
                (pnl.get("holdout_delta_total_return_vs_science") or {}) if isinstance(pnl, dict) else {}
            ).get("science_plus_sasang"),
            "economic_edge_claim_allowed": pnl.get("economic_edge_claim_allowed") if isinstance(pnl, dict) else False,
            "pnl_blockers": pnl.get("pnl_blockers") if isinstance(pnl, dict) else [],
            "note_ko": pnl.get("note_ko"),
        },
        "soft_vs_pnl_dual_reporting": {
            "soft_hit_primary": True,
            "pnl_secondary_reference_only": True,
            "headline_claim_allowed": False,
        },
        "walkforward": {
            "selection_top1_hit_rate": wf.get("selection_top1_hit_rate"),
            "mean_test_uplift_vs_science_alone": wf.get("mean_test_uplift_vs_science_alone"),
        },
        "conflict": [],
        "final_action": "RESEARCH_ATTACH_CANDIDATE" if attach_recommended else "HOLD",
        "recommended_lane": recommended_lane,
        "gates_primary_attach": True,
    }
    if cond_slim:
        kospi_slice["conditional_attach_research"] = cond_slim.get("kospi")
        k_hor = ((conditional_research or {}).get("instrument_slices") or {}).get("kospi", {}).get(
            "holdout_horizon"
        ) or {}
        if k_hor.get("horizon_attach_split_recommended"):
            kospi_slice["final_action"] = "RESEARCH_ATTACH_SHORT_1D_HYPOTHESIS"

    btc_slice: dict[str, Any] = {
        "instrument": "btc",
        "role": "auxiliary_observe_only",
        "field_id": "regime_science_core_v1_evaluation",
        "holdout_n": btc_aux.get("n_eval_dates"),
        "science_quant": {
            "science_core_short_1d_soft": science_b,
        },
        "lens_overlay": {
            "science_plus_sasang_short_1d_soft": sasang_b,
            "uplift_vs_science_short_1d_pp": uplift_b,
        },
        "conflict": [
            {
                "conflict_id": "kospi_btc_holdout_uplift_sign_mismatch",
                "kospi_uplift_pp_reference": holdout.get("kospi_holdout_uplift_soft"),
                "btc_uplift_pp": uplift_b,
                "parity_label": btc_aux.get("uplift_directional_parity_with_kospi"),
            }
        ],
        "final_action": btc_aux.get("auxiliary_recommendation") or "observe_only",
        "gates_primary_attach": bool(btc_aux.get("gates_primary_attach", False)),
        "note_ko": btc_aux.get("note_ko"),
    }
    if cond_slim:
        btc_slice["conditional_attach_research"] = cond_slim.get("btc")
        for hyp in ((cond_slim.get("btc_divergence") or {}).get("hypotheses") or []):
            if isinstance(hyp, dict):
                btc_slice["conflict"].append(
                    {
                        "conflict_id": hyp.get("id"),
                        "summary_ko": hyp.get("summary_ko"),
                    }
                )

    global_action_id = "WATCH_DAILY_TASK"
    if cond_slim and (cond_slim.get("final_action") or {}).get("action_id"):
        global_action_id = str((cond_slim.get("final_action") or {}).get("action_id"))

    reporting_order = ["Field", "Instrument slice", "Lens(role only)", "Conflict", "Final Action"]
    if cond_slim:
        reporting_order = [
            "Field",
            "Instrument slice",
            "Horizon/Shock subset",
            "Lens(role only)",
            "Conflict",
            "Final Action",
        ]

    return {
        "schema": "science_core_instrument_matrix_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": governance.get("track_wall") or "no_track_a_live_auto_merge",
        "field": {
            "field_id": "regime_science_core_v1_evaluation",
            "label_ko": "정량 데이터와 시장 심리 콤보 성능 검증 환경",
            "regime_primary_ssot": "regime_map (1차 실물 레짐; attach 트리거는 운영 게이트 별도)",
            "evaluation_window": window,
        },
        "lens_roles_contract": {
            "sasang": {
                "lens_key": "sasang",
                "role_ko": "단기 시장 심리(market sasang) overlay",
                "kospi_note": "KOSPI attach 1위 driver (instrument-specific)",
                "btc_note": "BTC holdout uplift may diverge; not attach driver",
            },
            "myeongni": {
                "lens_key": "myeongni",
                "role_ko": "중기 명리 overlay (2-way attach eligible)",
                "triple_note": "3-way observe_only; not in COMBO_LENS_IDS attach set",
            },
            "logos": {
                "lens_key": "logos",
                "role_ko": "거시 게이트·예언 콤보 실행 통제",
                "non_gating": True,
            },
        },
        "task_type_slices": {
            "science_core": {
                "description_ko": "per-date science JSONL + holdout + governance attach",
                "primary_instrument": "kospi",
                "auxiliary_instrument": "btc",
            },
            "prophecy": prophecy_slice,
            "compression_track_a": compression_slice,
        },
        "conditional_attach_research": cond_slim,
        "instrument_slices": {
            "kospi": kospi_slice,
            "btc": btc_slice,
        },
        "global_conflict": {
            "summary_ko": "KOSPI-BTC holdout uplift 부호 불일치 — BTC는 보조 관측만",
            "macro_blockers": composite.get("macro_blockers") or [],
        },
        "global_final_action": {
            "action_id": global_action_id,
            "detail_ko": "MKM-BTrack-DailyHypothesis-Chain (-IncludeScienceCoreLane) 및 신규 OHLCV 시 governance·conditional research 재판정",
            "track_a_ready": bool(promo.get("track_a_ready")),
            "live_trading_ready": bool(promo.get("live_trading_ready")),
            "horizon_hypothesis": ((cond_slim or {}).get("horizon_conditional_attach") or {}).get(
                "recommended_hypothesis"
            ),
        },
        "reporting_order": reporting_order,
        "fact_lock": {
            "governance_bundle": "docs/final/artifacts/science_core_governance_bundle_v1_latest.json",
            "governance_generated_at_utc": governance.get("generated_at_utc"),
            "research_attach_signoff": "docs/final/artifacts/science_core_research_attach_signoff_v1_latest.json",
            "conditional_attach_research": "docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json",
            "conditional_attach_generated_at_utc": (cond_slim or {}).get("generated_at_utc"),
            "prophecy_combo_sensitivity": "docs/final/artifacts/science_core_prophecy_combo_sensitivity_v1_latest.json",
            "prophecy_sensitivity_generated_at_utc": (prophecy_sensitivity or {}).get("generated_at_utc"),
        },
        "methodology_ko": (
            "instrument·task type별 SSOT 슬라이스. headline 숫자 합선 금지. "
            "Track A·실매매 자동 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOV)
    ap.add_argument("--attach-gate-json", type=Path, default=DEFAULT_ATTACH)
    ap.add_argument("--conditional-research-json", type=Path, default=DEFAULT_COND)
    ap.add_argument("--prophecy-sensitivity-json", type=Path, default=DEFAULT_PROPHECY_SENS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    gov = _load_json(args.governance_json)
    if not gov:
        print(f"ERROR: governance missing or invalid: {args.governance_json}", file=sys.stderr)
        return 2

    attach = _load_json(args.attach_gate_json)
    conditional = _load_json(args.conditional_research_json) if args.conditional_research_json.is_file() else None
    prophecy_sens = (
        _load_json(args.prophecy_sensitivity_json) if args.prophecy_sensitivity_json.is_file() else None
    )
    doc = build_matrix(
        governance=gov,
        attach_gate=attach,
        conditional_research=conditional,
        prophecy_sensitivity=prophecy_sens,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    kospi = doc["instrument_slices"]["kospi"]
    print(
        f"WROTE: {args.output.resolve()} kospi_uplift_pp={kospi['lens_overlay'].get('uplift_vs_science_short_1d_pp')} "
        f"action={doc['global_final_action']['action_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
