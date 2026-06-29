#!/usr/bin/env python3
"""[HYPO] B-track prophecy research freeze snapshot — read-only aggregate of *_latest artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_prophecy_research_freeze_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _leg_hits(score_path: Path) -> dict[str, Any]:
    doc = _load(score_path)
    if not doc:
        return {}
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    by: dict[str, dict[str, int]] = {}
    for r in rows:
        inst = str(r.get("instrument") or "").strip().lower()
        if not inst:
            continue
        by.setdefault(inst, {"n": 0, "h": 0})
        by[inst]["n"] += 1
        if str(r.get("predicted_direction") or "").lower() == str(r.get("actual_direction") or "").lower():
            by[inst]["h"] += 1
    out: dict[str, Any] = {}
    total_n = total_h = 0
    for inst, v in sorted(by.items()):
        n, h = int(v["n"]), int(v["h"])
        total_n += n
        total_h += h
        out[inst] = {"hit_rate": round(h / n, 6) if n else None, "n": n}
    if total_n:
        out["pooled"] = {"hit_rate": round(total_h / total_n, 6), "n": total_n}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--freeze-label", default="2026-06-12_regime_adaptive_lens_v1")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    lens_path = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
    gates_path = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"
    score_path = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    lens = _load(lens_path) or {}
    gates = _load(gates_path) or {}
    agg = lens.get("aggregate") if isinstance(lens.get("aggregate"), dict) else {}
    inputs = lens.get("inputs") if isinstance(lens.get("inputs"), dict) else {}

    report: dict[str, Any] = {
        "schema": "btrack_prophecy_research_freeze_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "freeze_label": str(args.freeze_label),
        "production_posture": {
            "send_gate": "HOLD",
            "track_a_auto_promote": False,
            "live_trading_auto_promote": False,
            "combined_all_passed": gates.get("combined_all_passed"),
            "outcome_class": gates.get("outcome_class"),
            "promotion_recommendation": gates.get("promotion_recommendation"),
        },
        "frozen_production_config": {
            "ensemble": "v1_dual_per_date",
            "lens_target": inputs.get("target_instrument", "kospi"),
            "lens_train_objective": inputs.get("train_objective", "beat_bull_first"),
            "lens_grid_profile": inputs.get("grid_profile", "kospi_bear_extended"),
            "regime_adaptive_lens_features": inputs.get("regime_adaptive_lens_features", True),
            "regime_expanded_bull_band": [
                inputs.get("regime_expanded_features_bull_min", 0.60),
                inputs.get("regime_expanded_features_bull_max", 0.625),
            ],
            "neutral_bps": (_load(score_path) or {}).get("neutral_bps", 2.0),
            "recent_trading_days": (_load(score_path) or {}).get("inputs", {}).get("recent_trading_days", 180)
            if isinstance((_load(score_path) or {}).get("inputs"), dict)
            else 180,
        },
        "metrics": {
            "lens_mean_test_accuracy": agg.get("mean_test_accuracy"),
            "lens_fraction_gt_beat_bull": agg.get("fraction_test_beats_always_bull"),
            "lens_fraction_gte_beat_bull": agg.get("fraction_test_meets_or_beats_always_bull"),
            "instrument_mean_test_accuracy": None,
            "price_hit_rates": _leg_hits(score_path),
        },
        "gates_blocked_by": [],
        "rejected_research_paths": [
            {
                "id": "always_on_expanded",
                "reason": "mean_wf_regression_0.627_vs_0.653_regime_adaptive",
            },
            {
                "id": "beat_bull_strict_first_and_margin_floor",
                "artifact": "reports/prophecy_lens_gt_tiebreak_ablation_v1_latest.json",
                "reason": "gt_0_5_all_variants",
            },
            {
                "id": "v2_confidence_fusion_per_date",
                "artifact": "reports/prophecy_dual_ensemble_structural_ablation_v1_latest.json",
                "reason": "pooled_hit_0.381_vs_0.528_baseline",
            },
            {
                "id": "micro_oscillator_neutral_and_override_all",
                "artifact": "reports/prophecy_micro_oscillator_tiebreak_ablation_v1_latest.json",
                "reason": "neutral_applied_0; causal_override_all_mean_0.533_vs_0.653",
            },
            {
                "id": "micro_oscillator_ambiguous_margin_sweep",
                "artifact": "reports/prophecy_micro_oscillator_ambiguous_ablation_v1_latest.json",
                "reason": "margin0_applied_0; m0.15_mean_0.633; m0.25_mean_0.533; gt_0_5_all",
            },
            {
                "id": "bbs_ms_hybrid_stale_daily_diff_60pct",
                "artifact": "reports/btrack_frozen30d_sim_pipeline_reconcile_v1_latest.json",
                "reason": "stale_daily_diff_4d_bull_bear_override; fresh_manifest_44.8pct_hybrid_43.3pct",
            },
            {
                "id": "holdout7_min_conf_below_018_for_0402",
                "artifact": "reports/btrack_holdout7_0402_conf_boundary_sweep_v1_latest.json",
                "reason": "lowering_min_conf_makes_0402_directional_bull_still_miss_on_bear; prod_0.18_frozen",
            },
        ],
        "pipeline_evidence": {
            "note": "exit_0 means runnable; combined_all_passed may still be false",
            "artifacts": {
                "lens_walkforward": str(lens_path.relative_to(ROOT)).replace("\\", "/"),
                "promotion_gates": str(gates_path.relative_to(ROOT)).replace("\\", "/"),
                "score_panel": str(score_path.relative_to(ROOT)).replace("\\", "/"),
                "gt_tiebreak_ablation": "reports/prophecy_lens_gt_tiebreak_ablation_v1_latest.json",
                "dual_ensemble_ablation": "reports/prophecy_dual_ensemble_structural_ablation_v1_latest.json",
                "beat_bull_policy_ablation": "reports/prophecy_lens_beat_bull_policy_ablation_v1_latest.json",
                "gte_human_signoff": "reports/prophecy_lens_beat_bull_gte_human_signoff_latest.json",
                "gte_research_shadow_gates": "reports/prophecy_promotion_gates_gte_research_shadow_v1_latest.json",
                "bbs_sim_pipeline_reconcile": "reports/btrack_frozen30d_sim_pipeline_reconcile_v1_latest.json",
                "bbs_hybrid_manifest": "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json",
                "holdout_gate_candidate": "reports/btrack_holdout_gate_candidate_v1_latest.json",
                "holdout7_composite_stack_eval": "reports/btrack_holdout7_composite_stack_eval_v1_latest.json",
                "holdout7_0402_conf_boundary_sweep": "reports/btrack_holdout7_0402_conf_boundary_sweep_v1_latest.json",
                "btc_lane2_oper_shadow_reconcile": "reports/btrack_btc_lane2_oper_shadow_reconcile_v1_latest.json",
                "btc_calibration_signoff_readiness": "reports/btrack_btc_calibration_wf_signoff_readiness_v1_latest.json",
                "btc_calibration_shadow_apply": "reports/btrack_btc_lane2_calibration_apply_recommended_180d_v1_latest.json",
                "btc_margin_wf_prod_aligned": "reports/btrack_btc_margin_walkforward_gate_prod_aligned_v1_latest.json",
                "lens_gt_structural_rd_brief": "reports/btrack_lens_gt_structural_rd_brief_v1_latest.json",
                "lens_always_bull_baseline_audit": "reports/prophecy_lens_always_bull_baseline_audit_v1_latest.json",
                "lens_gt_grid_expansion_ablation": "reports/prophecy_lens_gt_grid_expansion_ablation_v1_latest.json",
                "lens_multifold_refit_ablation": "reports/prophecy_lens_multifold_refit_ablation_v1_latest.json",
                "lens_gt_phase2_ablation": "reports/prophecy_lens_gt_phase2_ablation_v1_latest.json",
                "lens_gt_phase3_ablation": "reports/prophecy_lens_gt_phase3_ablation_v1_latest.json",
                "lens_gt_phase4_ablation": "reports/prophecy_lens_gt_phase4_ablation_v1_latest.json",
                "lens_regime_conditional_control_audit": "reports/prophecy_lens_regime_conditional_control_audit_v1_latest.json",
                "oper_30d_180d_panel_reconcile": "reports/btrack_oper_30d_180d_panel_reconcile_v1_latest.json",
                "frozen30d_bundle_v10": "reports/btrack_frozen30d_parallel_bundle_v10_latest.json",
            },
        },
        "holdout7_lane1_status": {},
        "btc_lane2_status": {},
        "btc_calibration_signoff_readiness": "reports/btrack_btc_calibration_wf_signoff_readiness_v1_latest.json",
        "gte_research_shadow_lane": {},
        "next_r_and_d": [
            "daily_dual_hypothesis_chain_observation_only",
            "holdout7_lane1_closed_advisory_only",
            "btc_lane2_shadow_documented",
            "bbs_ms_hybrid_holdout_safe_blend",
        ],
        "next_rd_brief": "reports/btrack_prophecy_next_rd_brief_v1_latest.json",
        "operator_lines": [],
    }

    h7_comp = _load(ROOT / "reports/btrack_holdout7_composite_stack_eval_v1_latest.json") or {}
    signed_stack = next(
        (s for s in (h7_comp.get("stacks") or []) if isinstance(s, dict) and s.get("stack_id") == "signed_bull_only"),
        {},
    )
    h7m = signed_stack.get("holdout7") if isinstance(signed_stack.get("holdout7"), dict) else {}
    ledger_line = (
        "Holdout7 ops: wrong_dir neutralized 6/6; headline miss 1 (04-02 advisory); "
        "min_conf<0.18 rejected; no Track A / oper promotion."
    )
    report["holdout7_lane1_status"] = {
        "lane_status": "CLOSED_RESEARCH_ONLY",
        "wrong_dir_neutralized": h7m.get("wrong_dir_neutralized"),
        "neutral_abstain_miss_remaining": h7m.get("neutral_abstain_miss_remaining"),
        "ops_wrong_dir_cover_rate": h7m.get("ops_wrong_dir_cover_rate"),
        "headline_directional_hit_rate_note": "6/6 is wrong_dir neutralization, not price headline hits",
        "min_conf_prod_frozen": 0.18,
        "oracle_upper_bound_non_promotable": True,
        "ledger_line": ledger_line,
        "artifact": "reports/btrack_holdout7_composite_stack_eval_v1_latest.json",
        "conf_boundary_sweep": "reports/btrack_holdout7_0402_conf_boundary_sweep_v1_latest.json",
    }

    lane2 = _load(ROOT / "reports/btrack_btc_lane2_oper_shadow_reconcile_v1_latest.json") or {}
    cal_apply = _load(ROOT / "reports/btrack_btc_lane2_calibration_apply_recommended_180d_v1_latest.json") or {}
    p180 = lane2.get("prod_aligned_180d") if isinstance(lane2.get("prod_aligned_180d"), dict) else {}
    cal180 = lane2.get("calibration_shadow_180d") if isinstance(lane2.get("calibration_shadow_180d"), dict) else {}
    report["btc_lane2_status"] = {
        "lane_status": lane2.get("lane_status", "SHADOW_DOCUMENTED"),
        "operational_score_unchanged": lane2.get("operational_score_unchanged", True),
        "type_a_prod_180d_delta_pp": p180.get("delta_pp"),
        "type_a_n_changes_180d": p180.get("n_changes"),
        "calibration_prod_180d_delta_pp": cal180.get("delta_pp"),
        "calibration_n_changes_180d": cal180.get("n_changes"),
        "calibration_signoff": cal180.get("signoff_decision", "PENDING"),
        "ledger_line": lane2.get("ledger_line"),
        "artifact": "reports/btrack_btc_lane2_oper_shadow_reconcile_v1_latest.json",
    }

    signoff_path = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_latest.json"
    gte_shadow_path = ROOT / "reports/prophecy_promotion_gates_gte_research_shadow_v1_latest.json"
    signoff = _load(signoff_path) or {}
    gte_shadow = _load(gte_shadow_path) or {}
    report["gte_research_shadow_lane"] = {
        "approved": bool(signoff.get("approved")),
        "decision": signoff.get("decision"),
        "gate_definition_change_acknowledged": bool(signoff.get("gate_definition_change_acknowledged")),
        "lens_beat_bull_comparator": "gte",
        "production_lens_beat_bull_comparator": "gt",
        "shadow_combined_all_passed": gte_shadow.get("combined_all_passed"),
        "note": "Research shadow only; does not change production recommended_chain gates.",
    }

    tr = gates.get("tracks") if isinstance(gates.get("tracks"), dict) else {}
    lens_tr = tr.get("per_date_lens") if isinstance(tr.get("per_date_lens"), dict) else {}
    inst_tr = tr.get("instrument_combo") if isinstance(tr.get("instrument_combo"), dict) else {}
    for g in lens_tr.get("gates") or []:
        if isinstance(g, dict) and g.get("passed") is False:
            report["gates_blocked_by"].append(g.get("gate_id"))
    for g in inst_tr.get("gates") or []:
        if isinstance(g, dict) and g.get("gate_id") == "instrument_wf_mean_test_accuracy":
            obs = g.get("observed") or {}
            if isinstance(obs, dict):
                report["metrics"]["instrument_mean_test_accuracy"] = obs.get("mean_test_accuracy")

    m = report["metrics"]
    ph = (m.get("price_hit_rates") or {}).get("pooled") or {}
    report["operator_lines"] = [
        f"- [B-FREEZE] {args.freeze_label}: v1 dual + regime-adaptive KOSPI lens FROZEN (research_only).",
        f"- [B-FREEZE] lens mean={m.get('lens_mean_test_accuracy')} gt_beat_bull={m.get('lens_fraction_gt_beat_bull')} "
        f"gte={m.get('lens_fraction_gte_beat_bull')} pooled_hit={ph.get('hit_rate')} n={ph.get('n')}.",
        f"- [B-FREEZE] combined_all_passed={report['production_posture'].get('combined_all_passed')} "
        f"blocked_by={report['gates_blocked_by']}; SEND_GATE=HOLD; Track A/live auto-merge OFF.",
        "- [B-FREEZE] exit_0 runnable != promotion OK; v2/strict_first rejected per ablation artifacts.",
        f"- [B-FREEZE] {ledger_line}",
        f"- [B-FREEZE] {lane2.get('ledger_line', 'BTC Lane2: see btc_lane2_oper_shadow_reconcile.')}",
        f"- [B-FREEZE] calibration shadow prod180d delta_pp={cal180.get('delta_pp')} "
        f"(WF global OOS higher; signoff {cal180.get('signoff_decision', 'PENDING')}).",
    ]
    gsl = report.get("gte_research_shadow_lane") or {}
    if gsl.get("approved"):
        report["operator_lines"].append(
            f"- [B-FREEZE] gte shadow APPROVED research_only; shadow_combined={gsl.get('shadow_combined_all_passed')}; "
            "prod lens comparator remains gt."
        )
    lens_rd = _load(ROOT / "reports/btrack_lens_gt_structural_rd_brief_v1_latest.json") or {}
    if lens_rd:
        report["operator_lines"].append(f"- [B-FREEZE] {lens_rd.get('ledger_line', 'Lens gt structural RD brief.')}")
    panel_rec = _load(ROOT / "reports/btrack_oper_30d_180d_panel_reconcile_v1_latest.json") or {}
    if panel_rec:
        report["operator_lines"].append(f"- [B-FREEZE] {panel_rec.get('ledger_line', 'Panel reconcile.')}")
    phase2 = _load(ROOT / "reports/prophecy_lens_gt_phase2_ablation_v1_latest.json") or {}
    if phase2:
        report["operator_lines"].append(f"- [B-FREEZE] {phase2.get('ledger_line', 'Lens gt phase2.')}")
    phase3 = _load(ROOT / "reports/prophecy_lens_gt_phase3_ablation_v1_latest.json") or {}
    if phase3:
        report["operator_lines"].append(f"- [B-FREEZE] {phase3.get('ledger_line', 'Lens gt phase3.')}")
    phase4 = _load(ROOT / "reports/prophecy_lens_gt_phase4_ablation_v1_latest.json") or {}
    if phase4:
        report["operator_lines"].append(f"- [B-FREEZE] {phase4.get('ledger_line', 'Lens gt phase4.')}")
    regime_audit = _load(ROOT / "reports/prophecy_lens_regime_conditional_control_audit_v1_latest.json") or {}
    if regime_audit:
        report["operator_lines"].append(f"- [B-FREEZE] {regime_audit.get('ledger_line', 'Regime control audit.')}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
