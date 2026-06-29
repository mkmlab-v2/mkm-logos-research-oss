#!/usr/bin/env python3
"""[HYPO] Lens gt beat-bull structural R&D brief — prod combined blocker (no oper promotion)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_lens_gt_structural_rd_brief_v1_latest.json"

FREEZE = ROOT / "reports/btrack_prophecy_research_freeze_v1_latest.json"
GT_TIEBREAK = ROOT / "reports/prophecy_lens_gt_tiebreak_ablation_v1_latest.json"
BEAT_BULL = ROOT / "reports/prophecy_lens_beat_bull_policy_ablation_v1_latest.json"
FOLD_REFIT = ROOT / "reports/prophecy_lens_fold_refit_ablation_v1_latest.json"
ALWAYS_BULL_AUDIT = ROOT / "reports/prophecy_lens_always_bull_baseline_audit_v1_latest.json"
GRID_EXPANSION = ROOT / "reports/prophecy_lens_gt_grid_expansion_ablation_v1_latest.json"
MULTIFOLD_REFIT = ROOT / "reports/prophecy_lens_multifold_refit_ablation_v1_latest.json"
PHASE2 = ROOT / "reports/prophecy_lens_gt_phase2_ablation_v1_latest.json"
PHASE3 = ROOT / "reports/prophecy_lens_gt_phase3_ablation_v1_latest.json"
PHASE4 = ROOT / "reports/prophecy_lens_gt_phase4_ablation_v1_latest.json"
REGIME_CONTROL_AUDIT = ROOT / "reports/prophecy_lens_regime_conditional_control_audit_v1_latest.json"
GTE_SIGNOFF = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_latest.json"
WF_REC = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
GATES_PROD = ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    freeze = _load(FREEZE)
    gt_ab = _load(GT_TIEBREAK)
    bb_ab = _load(BEAT_BULL)
    fold_ab = _load(FOLD_REFIT)
    gte_so = _load(GTE_SIGNOFF)
    wf = _load(WF_REC)
    gates = _load(GATES_PROD)
    bull_audit = _load(ALWAYS_BULL_AUDIT)
    grid_ab = _load(GRID_EXPANSION)
    mfold_ab = _load(MULTIFOLD_REFIT)
    phase2 = _load(PHASE2)
    phase3 = _load(PHASE3)
    phase4 = _load(PHASE4)
    regime_audit = _load(REGIME_CONTROL_AUDIT)

    metrics = freeze.get("metrics") or {}
    fold_detail = bb_ab.get("fold_detail") or []
    tie_folds = sum(
        1
        for f in fold_detail
        if isinstance(f, dict)
        and f.get("test_accuracy") == f.get("always_bull_control")
        and not f.get("gt_pass")
    )

    variants = [
        {
            "variant_id": v.get("variant_id"),
            "mean_test_accuracy": v.get("mean_test_accuracy"),
            "fraction_gt": v.get("fraction_test_beats_always_bull_gt"),
            "fraction_gte": v.get("fraction_test_meets_or_beats_always_bull_gte"),
            "train_objective": v.get("train_objective"),
            "train_min_margin_vs_bull": v.get("train_min_margin_vs_bull"),
        }
        for v in (gt_ab.get("variants") or [])
        if isinstance(v, dict)
    ]

    best_fold = fold_ab.get("best_by_gt_pass_then_accuracy") or {}
    best_margin = fold_ab.get("best_by_margin_vs_bull") or {}

    structural_experiments: list[dict[str, Any]] = [
        {
            "rank": 1,
            "id": "positive_margin_vs_always_bull",
            "status": "TRIED_NO_GT_PASS",
            "summary_ko": "train_min_margin·strict_first·grid expansion·multifold refit — gt 0/5 유지",
            "artifact": _rel(GRID_EXPANSION),
            "multifold_artifact": _rel(MULTIFOLD_REFIT),
        },
        {
            "rank": 1,
            "id": "always_bull_baseline_audit",
            "status": "DONE",
            "summary_ko": (bull_audit.get("verdict_ko") or "")[:200],
            "artifact": _rel(ALWAYS_BULL_AUDIT),
            "exact_tie_folds": (bull_audit.get("summary") or {}).get("exact_tie_with_prod_control"),
        },
        {
            "rank": 2,
            "id": "regime_adaptive_lens_feature_band",
            "status": "FROZEN_PROD",
            "summary_ko": "kospi_bear_extended + regime-adaptive bull band 0.60–0.625 — mean 65.3% but gt 0/5",
            "artifact": _rel(WF_REC),
        },
        {
            "rank": 3,
            "id": "fold_refit_expanded_prior",
            "status": "PARTIAL_SINGLE_FOLD",
            "summary_ko": "fold1 refit: best variant margin_vs_bull=0, gt_pass=false (full panel fraction_gt=0)",
            "artifact": _rel(FOLD_REFIT),
            "best_variant": best_fold.get("variant_id"),
            "best_margin_vs_bull": best_fold.get("margin_vs_bull"),
        },
        {
            "rank": 4,
            "id": "train_objective_family_sweep",
            "status": "TRIED_NO_GT_PASS",
            "summary_ko": "beat_bull_first vs beat_bull_strict_first — 모든 variant gt fraction 0",
            "artifact": _rel(GT_TIEBREAK),
        },
        {
            "rank": 5,
            "id": "gte_comparator_research_shadow",
            "status": "SHADOW_APPROVED_PROD_GT_UNCHANGED",
            "summary_ko": "gte would pass 5/5 folds; human sign-off research shadow only — prod comparator remains gt",
            "artifact": _rel(GTE_SIGNOFF),
            "gte_signoff_decision": gte_so.get("decision"),
        },
    ]

    prohibited = [
        "Auto-switch production lens comparator gt→gte without new structural gt pass evidence",
        "Promote combined_all_passed from gte shadow sign-off alone",
        "Merge BTC Lane2 instrument uplift as lens gt substitute",
    ]

    ledger = (
        "Lens gt 0/5: structural tie with always_bull on all WF folds; "
        "ablation sweeps failed gt; gte shadow approved research_only; prod gt frozen; no oper promotion."
    )

    report: dict[str, Any] = {
        "schema": "btrack_lens_gt_structural_rd_brief_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_promote": False,
        "send_gate": "HOLD",
        "production_blocker": {
            "gate_id": "lens_wf_fraction_folds_beat_always_bull_gt",
            "comparator_prod": "gt",
            "fraction_folds_pass_gt": metrics.get("lens_fraction_gt_beat_bull"),
            "fraction_folds_pass_gte": metrics.get("lens_fraction_gte_beat_bull"),
            "lens_wf_mean_test_accuracy": metrics.get("lens_mean_test_accuracy"),
            "combined_all_passed": (gates.get("combined_all_passed") if gates else None)
            or (freeze.get("production_posture") or {}).get("combined_all_passed"),
            "folds_tied_with_always_bull_not_gt": tie_folds,
            "fold_count_policy_ablation": len(fold_detail),
        },
        "root_cause_ko": (
            "WF test_accuracy가 fold마다 always_bull_control과 동일(tie) → strict gt(>) 미통과. "
            "mean accuracy 65%는 gte 기준으론 pass이나 prod는 gt 고정."
        ),
        "evidence_artifacts": {
            "freeze": _rel(FREEZE),
            "gt_tiebreak_ablation": _rel(GT_TIEBREAK),
            "beat_bull_policy_ablation": _rel(BEAT_BULL),
            "fold_refit_ablation": _rel(FOLD_REFIT),
            "always_bull_baseline_audit": _rel(ALWAYS_BULL_AUDIT),
            "gt_grid_expansion_ablation": _rel(GRID_EXPANSION),
            "multifold_refit_ablation": _rel(MULTIFOLD_REFIT),
            "phase2_anti_tie_bear_weighted": _rel(PHASE2),
            "phase3_architecture_ablation": _rel(PHASE3),
            "phase4_non_combo_anti_degen": _rel(PHASE4),
            "regime_conditional_control_audit": _rel(REGIME_CONTROL_AUDIT),
            "gte_human_signoff": _rel(GTE_SIGNOFF),
            "production_gates": _rel(GATES_PROD),
        },
        "phase_1a_audit_summary": bull_audit.get("summary"),
        "phase_1b_grid_best": grid_ab.get("best_by_gt_fraction"),
        "phase_1c_multifold_best": mfold_ab.get("best_by_fraction_folds_gt_pass"),
        "phase_2_anti_tie_bear_weighted": {
            "best_by_gt": phase2.get("best_by_gt_fraction"),
            "best_by_max_margin": phase2.get("best_by_max_fold_margin"),
            "verdict_ko": phase2.get("verdict_ko"),
        },
        "phase_3_architecture": {
            "best_by_gt": phase3.get("best_by_gt_fraction"),
            "best_by_max_margin": phase3.get("best_by_max_fold_margin"),
            "verdict_ko": phase3.get("verdict_ko"),
        },
        "phase_3a_regime_control_audit": regime_audit.get("summary"),
        "phase_4_non_combo_anti_degen": {
            "best_by_gt": phase4.get("best_by_gt_fraction"),
            "non_combo_paths": phase4.get("non_combo_paths"),
            "inference_shadow": phase4.get("inference_anti_degeneracy_shadow"),
            "verdict_ko": phase4.get("verdict_ko"),
        },
        "ablation_variant_table": variants,
        "fold_refit_highlights": {
            "best_by_gt_then_accuracy": {
                "variant_id": best_fold.get("variant_id"),
                "test_accuracy": best_fold.get("test_accuracy"),
                "always_bull_control": best_fold.get("always_bull_control"),
                "margin_vs_bull": best_fold.get("margin_vs_bull"),
                "gt_pass": best_fold.get("gt_pass"),
            },
            "best_by_margin_vs_bull": {
                "variant_id": best_margin.get("variant_id"),
                "margin_vs_bull": best_margin.get("margin_vs_bull"),
                "gt_pass": best_margin.get("gt_pass"),
            },
        },
        "structural_experiments_ranked": structural_experiments,
        "prohibited_auto_actions": prohibited,
        "next_structural_hypotheses": [
            "Combo+ensemble stack structurally tied to always_bull on WF — new lens family outside score-row/ensemble/combo required",
            "Hold combined blocker; daily ALERT_1 observation only until new structural gt pass",
            "BTC Lane2·calibration remain separate lanes — not lens gt substitute",
        ],
        "ledger_line": ledger,
        "operator_lines": [
            "- [LENS-GT-RD] research_only; prod comparator=gt; combined blocker unchanged.",
            f"- [LENS-GT-RD] gt={metrics.get('lens_fraction_gt_beat_bull')} gte={metrics.get('lens_fraction_gte_beat_bull')} "
            f"mean={metrics.get('lens_mean_test_accuracy')} ties_not_gt={tie_folds}/{len(fold_detail) or '?'}",
            "- [LENS-GT-RD] tiebreak+margin sweeps: all variants gt fraction 0.",
            f"- [LENS-GT-RD] gte shadow signoff={gte_so.get('decision')} — prod gt NOT switched.",
            f"- [LENS-GT-RD] 1a audit exact_tie={(bull_audit.get('summary') or {}).get('exact_tie_with_prod_control')}/"
            f"{(bull_audit.get('summary') or {}).get('n_folds')}.",
            f"- [LENS-GT-RD] 1b grid best_gt={(grid_ab.get('best_by_gt_fraction') or {}).get('variant_id')} "
            f"gt_frac={(grid_ab.get('best_by_gt_fraction') or {}).get('fraction_test_beats_always_bull_gt')}.",
            f"- [LENS-GT-RD] 1c multifold best={(mfold_ab.get('best_by_fraction_folds_gt_pass') or {}).get('variant_id')} "
            f"gt_frac={(mfold_ab.get('best_by_fraction_folds_gt_pass') or {}).get('fraction_folds_gt_pass')}.",
            f"- [LENS-GT-RD] 2 phase2 anti-tie/bear-weight best={(phase2.get('best_by_gt_fraction') or {}).get('variant_id')} "
            f"gt_frac={(phase2.get('best_by_gt_fraction') or {}).get('fraction_test_beats_always_bull_gt')}.",
            f"- [LENS-GT-RD] 3 phase3 architecture best={(phase3.get('best_by_gt_fraction') or {}).get('variant_id')} "
            f"gt_frac={(phase3.get('best_by_gt_fraction') or {}).get('fraction_test_beats_always_bull_gt')}.",
            f"- [LENS-GT-RD] 3a regime-control audit prod_gt={(regime_audit.get('summary') or {}).get('prod_gt_pass_folds')}/"
            f"{(regime_audit.get('summary') or {}).get('n_folds')}.",
            f"- [LENS-GT-RD] 4 non-combo+anti-degen best={(phase4.get('best_by_gt_fraction') or {}).get('path_id') or (phase4.get('best_by_gt_fraction') or {}).get('variant_id')} "
            f"gt_frac={(phase4.get('best_by_gt_fraction') or {}).get('fraction_test_beats_always_bull_gt')}.",
            "- [LENS-GT-RD] BTC Lane2 uplift does not clear lens gt; separate R&D track.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
