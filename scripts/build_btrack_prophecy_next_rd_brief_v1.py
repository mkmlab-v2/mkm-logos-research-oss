#!/usr/bin/env python3
"""[HYPO] Next meaningful B-track prophecy R&D brief (3 lanes) from holdout7/train_wrong/freeze SSOT."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_prophecy_next_rd_brief_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _run(script: str, *extra: str) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *extra]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    return {"script": script, "exit_code": rc, "ok": rc == 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--run-probes",
        action="store_true",
        help="Run bounded probes for all 3 lanes (may take several minutes).",
    )
    args = ap.parse_args()

    freeze = _load(ROOT / "reports/btrack_prophecy_research_freeze_v1_latest.json")
    train_wrong = _load(ROOT / "reports/btrack_train_wrong_pattern_summary_v1_latest.json")
    holdout_pack = _load(ROOT / "reports/btrack_holdout7_gate_research_pack_v1_latest.json")
    holdout_probe = _load(ROOT / "reports/btrack_holdout7_uncovered_four_probe_v1_latest.json")
    holdout_gate = _load(ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json")
    h7_composite = _load(ROOT / "reports/btrack_holdout7_composite_stack_eval_v1_latest.json")
    h7_conf_sweep = _load(ROOT / "reports/btrack_holdout7_0402_conf_boundary_sweep_v1_latest.json")
    btc_lane2 = _load(ROOT / "reports/btrack_btc_lane2_oper_shadow_reconcile_v1_latest.json")
    lens_gt_rd = _load(ROOT / "reports/btrack_lens_gt_structural_rd_brief_v1_latest.json")
    post_lens_multilens = _load(ROOT / "reports/btrack_post_lens_gt_multilens_lane_v1_latest.json")
    multilens_wf_gt = _load(ROOT / "reports/btrack_post_lens_gt_multilens_wf_gt_audit_v1_latest.json")
    post_lens_lane = _load(ROOT / "reports/btrack_post_lens_gt_multilens_lane_v1_latest.json")
    rq030_ptr = _load(ROOT / "reports/rq030_kospi_abstain_research_v1_latest.json")
    per_date_lens_252 = _load(ROOT / "reports/kospi_lens_ablation_per_date_252d_wf_window_v1_latest.json")
    panel_reconcile = _load(ROOT / "reports/btrack_oper_30d_180d_panel_reconcile_v1_latest.json")
    bbs_manifest = _load(ROOT / "reports/btrack_bbs_ms_hybrid_candidate_manifest_v1_latest.json")
    sim_reconcile = _load(ROOT / "reports/btrack_frozen30d_sim_pipeline_reconcile_v1_latest.json")
    v10 = _load(ROOT / "reports/btrack_frozen30d_parallel_bundle_v10_latest.json")
    hits = (freeze.get("metrics") or {}).get("price_hit_rates") or {}

    lanes: list[dict[str, Any]] = [
        {
            "lane_id": "holdout7_residual_trap",
            "lane_status": "CLOSED_RESEARCH_ONLY",
            "priority": 1,
            "title_ko": "Holdout7 Lane1 — CLOSED (04-02 advisory 잔여)",
            "hypothesis": "holdout_only OVN/pr_high 게이트 스택으로 bear_trap wrong_dir 중립화; train_wrong에는 미적용",
            "evidence": {
                "uncovered_by_either": (holdout_pack.get("findings") or {}).get("holdout7_uncovered_by_either_gate"),
                "holdout_gate_sim": train_wrong.get("holdout_gate_simulation"),
                "holdout7_pattern": train_wrong.get("holdout_7_wrong_dir"),
            },
            "blocked_promotion_reason": "headline ALERT_1 미개선; 6/6=wrong_dir neutralization only; Lane1 closed",
            "ledger_line": (
                "Holdout7 ops: wrong_dir neutralized 6/6; headline miss 1 (04-02 advisory); "
                "min_conf<0.18 rejected; no Track A / oper promotion."
            ),
            "probe_script": "build_btrack_holdout7_uncovered_four_probe_v1.py",
            "artifact": "reports/btrack_holdout7_uncovered_four_probe_v1_latest.json",
            "composite_stack": (holdout_probe.get("tradeoff_pr_high_vs_signed_bull") or {}).get(
                "stack_signed_bull_plus_neutral_miss"
            ),
            "gate_manifest_pointer": "reports/btrack_holdout_gate_candidate_v1_latest.json",
            "gate_manifest_summary": (holdout_gate.get("research_composite_stack") or {}),
            "composite_stack_eval": next(
                (s for s in (h7_composite.get("stacks") or []) if s.get("stack_id") == "composite_ops_advisory"),
                None,
            ),
            "composite_stack_eval_artifact": "reports/btrack_holdout7_composite_stack_eval_v1_latest.json",
            "conf_boundary_sweep_artifact": "reports/btrack_holdout7_0402_conf_boundary_sweep_v1_latest.json",
            "conf_boundary_sweep_verdict": (h7_conf_sweep.get("verdict_ko") or h7_conf_sweep.get("operator_lines")),
        },
        {
            "lane_id": "btc_instrument_leg_gap",
            "lane_status": "SHADOW_DOCUMENTED",
            "priority": 2,
            "title_ko": "BTC Lane2 — shadow documented (oper 180d +4.4pp; combined blocked)",
            "hypothesis": "instrument WF objective/nbps/beat_bull 정책 분리로 BTC 48%→55% 게이트 접근 (KOSPI lens 동결)",
            "evidence": {
                "btc_hit_rate": (hits.get("btc") or {}).get("hit_rate"),
                "kospi_hit_rate": (hits.get("kospi") or {}).get("hit_rate"),
                "instrument_wf_mean": freeze.get("metrics", {}).get("instrument_mean_test_accuracy"),
                "lens_gt_beat_bull": freeze.get("metrics", {}).get("lens_fraction_gt_beat_bull"),
                "lane2_reconcile": btc_lane2.get("prod_aligned_180d"),
            },
            "blocked_promotion_reason": "lens gt beat-bull 0/5가 prod combined blocker; BTC만 올려도 combined 미통과 가능",
            "probe_script": "build_btrack_btc_lane2_oper_shadow_reconcile_v1.py",
            "artifact": "reports/btrack_btc_lane2_oper_shadow_reconcile_v1_latest.json",
            "ledger_line": (
                "BTC Lane2: Type-A shadow on prod 180d +4.4pp (n_changes=16); oper 30d headline n_changes=0; "
                "lens gt 0/5 blocks combined; no oper/Track A promotion."
            ),
            "margin_wf_prod_aligned": "reports/btrack_btc_margin_walkforward_gate_prod_aligned_v1_latest.json",
            "calibration_shadow_apply": "reports/btrack_btc_lane2_calibration_apply_recommended_180d_v1_latest.json",
            "calibration_signoff_readiness": "reports/btrack_btc_calibration_wf_signoff_readiness_v1_latest.json",
        },
        {
            "lane_id": "bbs_ms_hybrid_holdout_safe",
            "priority": 3,
            "title_ko": "BBS+MS hybrid — frozen30d uplift vs holdout7 퇴화",
            "hypothesis": "ALERT_1 frozen30d +16.7pp 가능하나 holdout7 42.9%; holdout-safe blend 규칙 탐색",
            "evidence": {
                "hybrid_shadow": (holdout_pack.get("findings") or {}).get("hybrid_shadow_lane_bbs_ms"),
                "bbs_ms_pointer": "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json",
                "manifest_metrics": bbs_manifest.get("metrics_frozen_30d_btc"),
                "sim_pipeline_reconcile": sim_reconcile.get("metrics_compare"),
                "sim_reconcile_verdict_ko": sim_reconcile.get("verdict_ko"),
                "v10_hybrid_rule_matrix": next(
                    (
                        t.get("summary")
                        for t in (v10.get("parallel_tasks") or [])
                        if isinstance(t, dict) and t.get("task") == "hybrid_rule_matrix"
                    ),
                    None,
                ),
            },
            "blocked_promotion_reason": (
                "stale_daily_diff 60% debunked; manifest ~44.8% hybrid / holdout7 0%; "
                "do_not_replace_frozen_kpi_a_headline"
            ),
            "probe_script": "run_btrack_frozen30d_parallel_bundle_v10.py",
            "artifact": "reports/btrack_frozen30d_parallel_bundle_v10_latest.json",
            "reconcile_artifact": "reports/btrack_frozen30d_sim_pipeline_reconcile_v1_latest.json",
        },
        {
            "lane_id": "post_lens_gt_multilens_tsfm_outside_combo",
            "lane_status": "CLOSED_RESEARCH_ONLY",
            "priority": 4,
            "title_ko": "Post lens-gt — per_date multilens + TSFM (combo stack 밖) CLOSED",
            "hypothesis": "manseryeok session JSONL as-of 정적 multilens·TSFM XReg는 prod lens gt 대체가 아닌 별 축 탐색",
            "evidence": {
                "metric_wall_ko": post_lens_multilens.get("metric_wall_ko"),
                "per_date_best": per_date_lens_252.get("best_arm"),
                "per_date_sasang_myeongni_soft": next(
                    (
                        (a.get("metrics") or {}).get("soft_hit_rate")
                        for a in (per_date_lens_252.get("ranked_arms") or [])
                        if isinstance(a, dict) and a.get("arm_id") == "sasang_myeongni_only"
                    ),
                    None,
                ),
                "blocked_wf_per_date_ensemble": (
                    (post_lens_multilens.get("results_summary") or {})
                    .get("blocked_wf_directional_hr", {})
                    .get("per_date_kospi_ensemble_pooled")
                ),
                "timesfm_xreg_best_pooled": (
                    (post_lens_multilens.get("results_summary") or {})
                    .get("blocked_wf_directional_hr", {})
                    .get("timesfm25_xreg_best_pooled")
                ),
                "lens_gt_gt_fraction": (lens_gt_rd.get("production_blocker") or {}).get(
                    "fraction_folds_pass_gt"
                ),
                "blocked_wf_multilens_gt_best": multilens_wf_gt.get("best_by_gt_fraction"),
                "blocked_wf_multilens_gt_audit": "reports/btrack_post_lens_gt_multilens_wf_gt_audit_v1_latest.json",
            },
            "blocked_promotion_reason": post_lens_multilens.get("blocked_promotion_reason")
            or "soft/WF HR≠prod lens gt; combined blocker unchanged",
            "probe_script": "run_btrack_post_lens_gt_multilens_wf_gt_audit_v1.py",
            "artifact": "reports/btrack_post_lens_gt_multilens_lane_v1_latest.json",
            "wf_gt_audit_artifact": "reports/btrack_post_lens_gt_multilens_wf_gt_audit_v1_latest.json",
            "ledger_line": (
                "Post lens-gt multilens lane CLOSED: WF gt 0/4; macro WF gt 0/4; "
                "RQ-030 abstain≠prod gt; combined blocker unchanged."
            ),
        },
    ]

    probe_runs: list[dict[str, Any]] = []
    if args.run_probes:
        for lane in lanes:
            script = str(lane.get("probe_script") or "")
            if script:
                probe_runs.append(_run(script))

    lane_results: list[dict[str, Any]] = []
    for lane in lanes:
        art = _load(ROOT / str(lane.get("artifact")))
        lane_results.append(
            {
                **lane,
                "probe_artifact_present": bool(art),
                "probe_summary": {
                    "operator_lines": art.get("operator_lines", [])[:4],
                    "auto_promote": art.get("auto_promote"),
                    "best_probe": art.get("best_probe"),
                    "metrics": art.get("metrics"),
                }
                if art
                else None,
            }
        )

    report: dict[str, Any] = {
        "schema": "btrack_prophecy_next_rd_brief_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "frozen_baseline": freeze.get("freeze_label"),
        "production_posture": freeze.get("production_posture"),
        "lanes": lane_results,
        "probe_runs": probe_runs if probe_runs else None,
        "operator_lines": [
            "- [NEXT-RD] 4 lanes: holdout7 / BTC / BBS hybrid / post-lens-gt multilens+TSFM.",
            "- [NEXT-RD] None auto-promote; prod lens gt beat-bull 0/5 remains unless new structural pass.",
            "- [NEXT-RD] train_wrong≠holdout7 — holdout_only boundary per train_wrong_pattern SSOT.",
            f"- [NEXT-RD] pooled_hit={(hits.get('pooled') or {}).get('hit_rate')} n={(hits.get('pooled') or {}).get('n')}.",
            f"- [NEXT-RD] holdout7 ops signed_bull wrong_neutralized="
            f"{((next((s for s in (h7_composite.get('stacks') or []) if s.get('stack_id') == 'signed_bull_only'), {}) or {}).get('holdout7') or {}).get('wrong_dir_neutralized', '?')}/6; "
            f"04-02 neutral_miss=1 advisory-only; conf<0.18 → bull miss (keep prod 0.18).",
            f"- [NEXT-RD] BTC cal shadow prod180d delta_pp="
            f"{((btc_lane2.get('calibration_shadow_180d') or {}).get('delta_pp'))} "
            f"(WF OOS optimistic; signoff="
            f"{((btc_lane2.get('calibration_shadow_180d') or {}).get('signoff_decision') or 'PENDING')}).",
            f"- [NEXT-RD] BBS hybrid manifest "
            f"{((bbs_manifest.get('metrics_frozen_30d_btc') or {}).get('bbs_ms_hybrid_all_rows'))} "
            f"(reconcile: stale 60% debunked; pipeline hybrid "
            f"{((sim_reconcile.get('metrics_compare') or {}).get('pipeline_bull_bear_split_hybrid'))}).",
            f"- [NEXT-RD] Lens gt structural brief: "
            f"{((lens_gt_rd.get('production_blocker') or {}).get('fraction_folds_pass_gt'))} gt; "
            f"ledger={(lens_gt_rd.get('ledger_line') or '')[:80]}…",
            f"- [NEXT-RD] 30d/180d panel reconcile: oper30 n_changes="
            f"{((panel_reconcile.get('panels') or {}).get('oper_headline_30d') or {}).get('n_changes')} "
            f"vs rec180 n_changes="
            f"{((panel_reconcile.get('panels') or {}).get('recommended_180d_prod_aligned') or {}).get('n_changes')}.",
            f"- [NEXT-RD] Post lens-gt multilens CLOSED: WF gt="
            f"{((multilens_wf_gt.get('best_by_gt_fraction') or {}).get('fraction_test_beats_always_bull_gt'))}; "
            f"RQ-030 abstain pooled="
            f"{((rq030_ptr.get('best_honest_beat_majority') or {}).get('pooled_test_directional_hit_rate'))} "
            f"(≠ prod gt).",
        ],
        "auto_promote": False,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
