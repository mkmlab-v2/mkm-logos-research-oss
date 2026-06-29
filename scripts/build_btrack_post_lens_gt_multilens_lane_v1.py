#!/usr/bin/env python3
"""[HYPO] Post lens-gt-closure multilens / TSFM lane bundle (research_only, separate metric wall)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/btrack_post_lens_gt_multilens_lane_v1_latest.json"
SCHEMA = "btrack_post_lens_gt_multilens_lane_v1"

PER_DATE_252 = ROOT / "reports/kospi_lens_ablation_per_date_252d_wf_window_v1_latest.json"
PER_DATE_252_MACRO = ROOT / "reports/kospi_lens_ablation_per_date_252d_macro_wf_window_v1_latest.json"
WF_GT_AUDIT = ROOT / "reports/btrack_post_lens_gt_multilens_wf_gt_audit_v1_latest.json"
WF_GT_AUDIT_MACRO = ROOT / "reports/btrack_post_lens_gt_multilens_wf_gt_audit_macro_v1_latest.json"
RQ030_POINTER = ROOT / "reports/rq030_kospi_abstain_research_v1_latest.json"
WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
TIMESFM_XREG = ROOT / "reports/rq025_timesfm25_kospi_xreg_wf_shadow_v1_latest.json"
LENS_GT_RD = ROOT / "reports/btrack_lens_gt_structural_rd_brief_v1_latest.json"
FREEZE = ROOT / "reports/btrack_prophecy_research_freeze_v1_latest.json"


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


def _arm_soft(doc: dict[str, Any], arm_id: str) -> float | None:
    for row in doc.get("ranked_arms") or []:
        if isinstance(row, dict) and row.get("arm_id") == arm_id:
            m = row.get("metrics") or {}
            try:
                return float(m.get("soft_hit_rate"))
            except (TypeError, ValueError):
                return None
    return None


def _wf_arm_pooled(doc: dict[str, Any], arm_id: str) -> float | None:
    for row in ((doc.get("blocked_walkforward_test_only") or {}).get("arms") or []):
        if isinstance(row, dict) and row.get("arm_id") == arm_id:
            try:
                return float(row.get("pooled_test_directional_hit_rate"))
            except (TypeError, ValueError):
                return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    per_date = _load(PER_DATE_252)
    per_date_macro = _load(PER_DATE_252_MACRO)
    wf_gt_audit = _load(WF_GT_AUDIT)
    wf_gt_audit_macro = _load(WF_GT_AUDIT_MACRO)
    rq030 = _load(RQ030_POINTER)
    wf = _load(WF_COMPARE)
    xreg = _load(TIMESFM_XREG)
    lens_gt = _load(LENS_GT_RD)
    freeze = _load(FREEZE)

    best_per_date = (per_date.get("best_arm") or {}) if per_date else {}
    best_macro = (per_date_macro.get("best_arm") or {}) if per_date_macro else {}

    xreg_arms = ((xreg.get("blocked_walkforward_test_only") or {}).get("arms") or [])
    best_xreg = xreg.get("best_xreg_arm") or {}
    if not best_xreg and xreg_arms:
        best_xreg = max(
            (a for a in xreg_arms if isinstance(a, dict) and a.get("pooled_test_directional_hit_rate") is not None),
            key=lambda a: float(a["pooled_test_directional_hit_rate"]),
            default={},
        )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lane_id": "post_lens_gt_multilens_tsfm_outside_combo",
        "lane_status": "CLOSED_RESEARCH_ONLY",
        "closure_verdict_ko": (
            "per_date multilens·macro as-of·blocked WF gt·RQ-030 abstain 모두 prod strict gt(0/4~0/5) 미통과. "
            "directional HR/abstain majority beat은 combined blocker 대체 불가."
        ),
        "frozen_baseline": freeze.get("freeze_label"),
        "production_posture": freeze.get("production_posture"),
        "metric_wall_ko": (
            "본 lane은 calendar soft HR·blocked WF directional HR만 보고한다. "
            "prod lens WF strict gt beat-bull(0/5)과 다른 축이며 combined blocker 대체·승격 근거가 아니다."
        ),
        "lens_gt_closure_pointer": str(LENS_GT_RD.relative_to(ROOT)).replace("\\", "/"),
        "lens_gt_gt_fraction": (lens_gt.get("production_blocker") or {}).get("fraction_folds_pass_gt"),
        "artifacts": {
            "per_date_multilens_252d": str(PER_DATE_252.relative_to(ROOT)).replace("\\", "/"),
            "per_date_multilens_252d_macro": str(PER_DATE_252_MACRO.relative_to(ROOT)).replace("\\", "/"),
            "blocked_wf_compare": str(WF_COMPARE.relative_to(ROOT)).replace("\\", "/"),
            "blocked_wf_multilens_gt_audit": str(WF_GT_AUDIT.relative_to(ROOT)).replace("\\", "/"),
            "blocked_wf_multilens_gt_audit_macro": str(WF_GT_AUDIT_MACRO.relative_to(ROOT)).replace("\\", "/"),
            "rq030_abstain_pointer": str(RQ030_POINTER.relative_to(ROOT)).replace("\\", "/"),
            "timesfm_xreg_wf_shadow": str(TIMESFM_XREG.relative_to(ROOT)).replace("\\", "/"),
        },
        "window_aligned": {
            "date_from": "2025-05-28",
            "date_to": "2026-06-10",
            "eval_days": 252,
            "neutral_bps": 5.0,
        },
        "results_summary": {
            "per_date_jsonl_calendar_soft_hr": {
                "best_arm_id": best_per_date.get("arm_id"),
                "soft_hit_rate": ((best_per_date.get("metrics") or {}).get("soft_hit_rate")),
                "directional_hit_rate": ((best_per_date.get("metrics") or {}).get("directional_hit_rate")),
                "sasang_myeongni_only_soft": _arm_soft(per_date, "sasang_myeongni_only"),
                "lens3_runtime_soft": _arm_soft(per_date, "lens3_runtime"),
            },
            "per_date_jsonl_macro_calendar_soft_hr": {
                "best_arm_id": best_macro.get("arm_id"),
                "soft_hit_rate": ((best_macro.get("metrics") or {}).get("soft_hit_rate")),
            },
            "blocked_wf_gt_audit": {
                "best_arm_id": (wf_gt_audit.get("best_by_gt_fraction") or {}).get("arm_id"),
                "best_gt_fraction": (wf_gt_audit.get("best_by_gt_fraction") or {}).get(
                    "fraction_test_beats_always_bull_gt"
                ),
                "lens3_4ai_gt_fraction": next(
                    (
                        a.get("fraction_test_beats_always_bull_gt")
                        for a in ((wf_gt_audit.get("blocked_walkforward_gt_audit") or {}).get("arms") or [])
                        if isinstance(a, dict) and a.get("arm_id") == "lens3_4ai_overlay"
                    ),
                    None,
                ),
                "lens3_4ai_pooled_directional": next(
                    (
                        a.get("pooled_test_directional_hit_rate")
                        for a in ((wf_gt_audit.get("blocked_walkforward_gt_audit") or {}).get("arms") or [])
                        if isinstance(a, dict) and a.get("arm_id") == "lens3_4ai_overlay"
                    ),
                    None,
                ),
                "prod_lens_combo_gt_fraction": (wf_gt_audit.get("compare_pointers") or {}).get(
                    "prod_lens_combo_gt_fraction"
                ),
            },
            "blocked_wf_gt_audit_macro": {
                "best_gt_fraction": (wf_gt_audit_macro.get("best_by_gt_fraction") or {}).get(
                    "fraction_test_beats_always_bull_gt"
                ),
                "lens3_4ai_pooled_directional": next(
                    (
                        a.get("pooled_test_directional_hit_rate")
                        for a in ((wf_gt_audit_macro.get("blocked_walkforward_gt_audit") or {}).get("arms") or [])
                        if isinstance(a, dict) and a.get("arm_id") == "lens3_4ai_overlay"
                    ),
                    None,
                ),
            },
            "rq030_per_date_abstain": {
                "wf_majority_pooled_hr": rq030.get("wf_majority_baseline_pooled_hr"),
                "per_date_full_pooled_hr": rq030.get("per_date_full_pooled_hr"),
                "best_honest_beat_majority": rq030.get("best_honest_beat_majority"),
                "rq030b_nested_beats_majority": rq030.get("rq030b_nested_beats_majority"),
                "note_ko": "abstain beat-majority=directional HR 축; prod lens gt 아님",
            },
            "blocked_wf_directional_hr": {
                "per_date_kospi_ensemble_pooled": _wf_arm_pooled(wf, "per_date_kospi_ensemble"),
                "timesfm25_xreg_best_arm_id": best_xreg.get("arm_id"),
                "timesfm25_xreg_best_pooled": best_xreg.get("pooled_test_directional_hit_rate"),
                "timesfm25_zero_shot_pooled": (xreg.get("compare_pointers") or {}).get(
                    "timesfm25_zero_shot_pooled_hr"
                ),
                "flow_classical_straw_man_pooled": (xreg.get("compare_pointers") or {}).get(
                    "flow_foreign_lag1_classical_pooled_hr"
                ),
                "flow_classical_caveat": (xreg.get("compare_pointers") or {}).get("flow_classical_caveat"),
            },
        },
        "blocked_promotion_reason": (
            "combo/non-combo lens gt stack closed at 0/5 gt; multilens soft HR≠prod lens gt; "
            "no combined_all_passed; no Track A / oper / live auto-merge"
        ),
        "probe_scripts": [
            "run_kospi_lens_ablation_backtest_v1.py --lens-source per_date_jsonl",
            "run_btrack_post_lens_gt_multilens_wf_gt_audit_v1.py",
            "run_rq030_kospi_per_date_abstain_wf_sweep_v1.py",
            "run_rq025_timesfm25_kospi_xreg_wf_shadow_v1.py",
        ],
        "next_within_lane": [],
        "ledger_line": (
            "Post lens-gt multilens lane CLOSED: WF gt 0/4; macro WF gt 0/4; "
            "RQ-030 abstain≠prod gt; combined blocker unchanged."
        ),
        "operator_lines": [],
    }

    pd_best = report["results_summary"]["per_date_jsonl_calendar_soft_hr"]
    wf_ens = report["results_summary"]["blocked_wf_directional_hr"]["per_date_kospi_ensemble_pooled"]
    xreg_p = report["results_summary"]["blocked_wf_directional_hr"]["timesfm25_xreg_best_pooled"]
    wf_gt = report["results_summary"].get("blocked_wf_gt_audit") or {}
    rq030_best = (report["results_summary"].get("rq030_per_date_abstain") or {}).get("best_honest_beat_majority") or {}
    macro_gt = report["results_summary"].get("blocked_wf_gt_audit_macro") or {}
    report["operator_lines"] = [
        "- [POST-LENS-GT] CLOSED research_only; prod lens gt 0/5 unchanged.",
        f"- [POST-LENS-GT] multilens WF gt={wf_gt.get('best_gt_fraction')} macro_WF gt={macro_gt.get('best_gt_fraction')}.",
        f"- [POST-LENS-GT] lens3_4ai pooled_dir={wf_gt.get('lens3_4ai_pooled_directional')} (gt still 0).",
        f"- [POST-LENS-GT] RQ-030 abstain best={rq030_best.get('grid_id')} pooled={rq030_best.get('pooled_test_directional_hit_rate')} "
        f"(≠ prod gt).",
        "- [POST-LENS-GT] no combined promotion; SEND_GATE HOLD.",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
