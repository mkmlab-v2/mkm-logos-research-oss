#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], dry_run: bool) -> int:
    print(" ".join(cmd))
    if dry_run:
        return 0
    cp = subprocess.run(cmd, check=False)
    return int(cp.returncode)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run canon-only singularity report + balanced + lane summary chain."
    )
    ap.add_argument("--canon-jsonl", default="data/logos/verse_decoded_v2.jsonl")
    ap.add_argument("--regime-map-json", default="data/regimes/regime_map_btc_ext.json")
    ap.add_argument("--top-n", type=int, default=50)
    ap.add_argument("--quota-per-regime", type=int, default=12)
    ap.add_argument(
        "--report-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_only_v1.json",
    )
    ap.add_argument(
        "--balanced-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_balanced_canon_only_v1.json",
    )
    ap.add_argument(
        "--summary-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_lane_summary_v1.json",
    )
    ap.add_argument(
        "--quality-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_v1.json",
    )
    ap.add_argument(
        "--quality-gate-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_history_v1.jsonl",
    )
    ap.add_argument(
        "--quality-gate-health-summary-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_health_summary_v1.json",
    )
    ap.add_argument(
        "--quality-gate-policy-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_policy_eval_v1.json",
    )
    ap.add_argument(
        "--insight-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_v1.json",
    )
    ap.add_argument(
        "--insight-quality-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_quality_gate_v1.json",
    )
    ap.add_argument(
        "--insight-explainability-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_v1.json",
    )
    ap.add_argument(
        "--insight-explainability-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_quality_gate_v1.json",
    )
    ap.add_argument(
        "--insight-explainability-benchmark-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_benchmark_cohort_v1.jsonl",
    )
    ap.add_argument("--insight-explainability-benchmark-top-n", type=int, default=20)
    ap.add_argument(
        "--insight-explainability-benchmark-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_benchmark_gate_v1.json",
    )
    ap.add_argument("--insight-explainability-benchmark-min-coverage", type=float, default=0.7)
    ap.add_argument("--insight-explainability-benchmark-min-driver-accuracy", type=float, default=0.7)
    ap.add_argument("--insight-explainability-benchmark-min-regime-accuracy", type=float, default=0.7)
    ap.add_argument("--insight-explainability-benchmark-min-reviewed-count", type=int, default=3)
    ap.add_argument("--require-explainability-benchmark", action="store_true")
    ap.add_argument(
        "--insight-slice-stability-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_slice_stability_v1.json",
    )
    ap.add_argument(
        "--insight-slice-stability-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_slice_stability_quality_gate_v1.json",
    )
    ap.add_argument("--insight-slice-stability-window", type=int, default=3)
    ap.add_argument("--insight-max-slice-change-count", type=int, default=5)
    ap.add_argument(
        "--weekly-brief-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_v1.json",
    )
    ap.add_argument(
        "--weekly-brief-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_v1.md",
    )
    ap.add_argument(
        "--weekly-brief-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_quality_gate_v1.json",
    )
    ap.add_argument(
        "--weekly-false-alert-review-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_false_alert_review_v1.json",
    )
    ap.add_argument(
        "--operational-consistency-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_operational_consistency_check_v1.json",
    )
    ap.add_argument(
        "--promotion-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_gate_v1.json",
    )
    ap.add_argument(
        "--promotion-gate-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_gate_history_v1.jsonl",
    )
    ap.add_argument(
        "--promotion-dashboard-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_dashboard_v1.json",
    )
    ap.add_argument(
        "--promotion-dashboard-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_dashboard_v1.md",
    )
    ap.add_argument(
        "--promotion-alert-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_alert_v1.json",
    )
    ap.add_argument(
        "--promotion-alert-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_alert_v1.md",
    )
    ap.add_argument(
        "--promotion-alert-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_alert_history_v1.jsonl",
    )
    ap.add_argument(
        "--promotion-readiness-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_readiness_report_v1.json",
    )
    ap.add_argument(
        "--promotion-readiness-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_readiness_report_v1.md",
    )
    ap.add_argument(
        "--promotion-go-no-go-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json",
    )
    ap.add_argument(
        "--promotion-go-no-go-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.md",
    )
    ap.add_argument(
        "--regime-calibration-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_regime_calibration_round_v1.json",
    )
    ap.add_argument(
        "--day7-checkpoint-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_day7_checkpoint_gate_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v1-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2.md",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-rollover-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-rollover-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_v1.md",
    )
    ap.add_argument(
        "--strict-baseline-freeze-diff-v2-from-v1-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_diff_v2_from_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-diff-v2-from-v1-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_diff_v2_from_v1.md",
    )
    ap.add_argument(
        "--strict-baseline-freeze-vfinal-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-vfinal-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.md",
    )
    ap.add_argument(
        "--strict-baseline-freeze-generation-diff-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-generation-diff-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_generation_diff_vfinal_v1.md",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-rollover-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_history_v1.jsonl",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-stability-gate-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--strict-baseline-freeze-v2-stability-gate-output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.md",
    )
    ap.add_argument("--strict-baseline-freeze-v2-stability-window", type=int, default=7)
    ap.add_argument("--strict-baseline-freeze-v2-stability-min-window-size", type=int, default=5)
    ap.add_argument("--strict-baseline-freeze-v2-stability-min-frozen-rate", type=float, default=0.85)
    ap.add_argument("--weekly-brief-window", type=int, default=7)
    ap.add_argument("--consistency-window", type=int, default=3)
    ap.add_argument("--promotion-required-health-level", default="green")
    ap.add_argument("--promotion-max-false-alert-flags", type=int, default=0)
    ap.add_argument("--promotion-max-delta-changed-count", type=int, default=2)
    ap.add_argument("--promotion-window", type=int, default=7)
    ap.add_argument("--promotion-min-pass-rate", type=float, default=0.85)
    ap.add_argument("--promotion-window-long", type=int, default=14)
    ap.add_argument("--promotion-long-min-pass-rate", type=float, default=0.85)
    ap.add_argument("--enforce-promotion", action="store_true")
    ap.add_argument(
        "--insight-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_history_v1.jsonl",
    )
    ap.add_argument(
        "--insight-delta-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_delta_summary_v1.json",
    )
    ap.add_argument("--insight-delta-min-score", type=float, default=0.001)
    ap.add_argument("--auto-apply-calibration", action="store_true")
    ap.add_argument(
        "--regime-calibration-input-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_regime_calibration_round_v1.json",
    )
    ap.add_argument(
        "--delta-cutoff-autotune-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_delta_cutoff_autotune_v1.json",
    )
    ap.add_argument(
        "--delta-cutoff-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_delta_cutoff_update_history_v1.jsonl",
    )
    ap.add_argument("--delta-cutoff-max-relative-step", type=float, default=0.10)
    ap.add_argument("--delta-cutoff-min-changed-count", type=int, default=3)
    ap.add_argument("--delta-cutoff-floor", type=float, default=0.0005)
    ap.add_argument("--delta-cutoff-ceil", type=float, default=0.0050)
    ap.add_argument(
        "--delta-cutoff-governance-output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_delta_cutoff_governance_gate_v1.json",
    )
    ap.add_argument("--delta-governance-window", type=int, default=20)
    ap.add_argument("--delta-governance-min-window-size", type=int, default=5)
    ap.add_argument("--delta-governance-min-apply-rate", type=float, default=0.10)
    ap.add_argument("--delta-governance-max-hold-streak", type=int, default=10)
    ap.add_argument("--enforce-delta-governance", action="store_true")
    ap.add_argument("--insight-delta-min-score-bull-pump", type=float, default=None)
    ap.add_argument("--insight-delta-min-score-sideways-accumulation", type=float, default=None)
    ap.add_argument("--insight-delta-min-score-bear-trend", type=float, default=None)
    ap.add_argument("--insight-delta-min-score-capitulation", type=float, default=None)
    ap.add_argument("--insight-top-n", type=int, default=12)
    ap.add_argument("--skip-insight", action="store_true")
    ap.add_argument("--quality-gate-health-window", type=int, default=30)
    ap.add_argument("--enforce-health", action="store_true")
    ap.add_argument("--health-max-fail-count", type=int, default=0)
    ap.add_argument("--health-min-pass-rate", type=float, default=1.0)
    ap.add_argument("--health-allow-yellow", action="store_true")
    ap.add_argument("--summary-top-n", type=int, default=20)
    ap.add_argument("--expected-canon-rows", type=int, default=28741)
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    py = sys.executable

    cmd_report = [
        py,
        str(root / "scripts" / "core" / "build_original_corpus_regime_singularity_report_v1.py"),
        "--canon-only",
        "--canon-jsonl",
        str(args.canon_jsonl),
        "--top-n",
        str(int(args.top_n)),
        "--output-json",
        str(args.report_output_json),
    ]
    cmd_balanced = [
        py,
        str(root / "scripts" / "core" / "build_original_corpus_regime_singularity_balanced_report_v1.py"),
        "--canon-only",
        "--canon-jsonl",
        str(args.canon_jsonl),
        "--regime-map-json",
        str(args.regime_map_json),
        "--quota-per-regime",
        str(int(args.quota_per_regime)),
        "--output-json",
        str(args.balanced_output_json),
    ]
    cmd_summary = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_lane_summary_v1.py"),
        "--input-json",
        str(args.report_output_json),
        "--top-n",
        str(int(args.summary_top_n)),
        "--output-json",
        str(args.summary_output_json),
    ]
    cmd_validate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_outputs_v1.py"),
        "--report-json",
        str(args.report_output_json),
        "--balanced-json",
        str(args.balanced_output_json),
        "--summary-json",
        str(args.summary_output_json),
        "--expected-canon-rows",
        str(int(args.expected_canon_rows)),
        "--output-json",
        str(args.quality_gate_output_json),
        "--history-jsonl",
        str(args.quality_gate_history_jsonl),
    ]
    cmd_health_summary = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_gate_health_summary_v1.py"),
        "--history-jsonl",
        str(args.quality_gate_history_jsonl),
        "--window",
        str(int(args.quality_gate_health_window)),
        "--output-json",
        str(args.quality_gate_health_summary_json),
    ]
    cmd_enforce_health = [
        py,
        str(root / "scripts" / "core" / "enforce_canon_singularity_gate_health_v1.py"),
        "--health-summary-json",
        str(args.quality_gate_health_summary_json),
        "--max-fail-count",
        str(int(args.health_max_fail_count)),
        "--min-pass-rate",
        str(float(args.health_min_pass_rate)),
        "--output-json",
        str(args.quality_gate_policy_output_json),
    ]
    if bool(args.health_allow_yellow):
        cmd_enforce_health.append("--allow-yellow")
    cmd_insight = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_insight_minimum_v1.py"),
        "--summary-json",
        str(args.summary_output_json),
        "--top-n",
        str(int(args.insight_top_n)),
        "--output-json",
        str(args.insight_output_json),
        "--history-jsonl",
        str(args.insight_history_jsonl),
    ]
    cmd_insight_gate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_insight_minimum_v1.py"),
        "--input-json",
        str(args.insight_output_json),
        "--output-json",
        str(args.insight_quality_gate_output_json),
    ]
    effective_min_score_delta = float(args.insight_delta_min_score)
    if bool(args.auto_apply_calibration):
        cmd_autotune = [
            py,
            str(root / "scripts" / "core" / "build_canon_singularity_delta_cutoff_autotune_v1.py"),
            "--calibration-json",
            str(args.regime_calibration_input_json),
            "--current-min-score-delta",
            str(float(args.insight_delta_min_score)),
            "--max-relative-step",
            str(float(args.delta_cutoff_max_relative_step)),
            "--min-changed-count",
            str(int(args.delta_cutoff_min_changed_count)),
            "--floor",
            str(float(args.delta_cutoff_floor)),
            "--ceil",
            str(float(args.delta_cutoff_ceil)),
            "--output-json",
            str(args.delta_cutoff_autotune_output_json),
            "--history-jsonl",
            str(args.delta_cutoff_history_jsonl),
        ]
        rc_autotune = _run(cmd_autotune, dry_run=bool(args.dry_run))
        if rc_autotune != 0:
            return rc_autotune
        if not bool(args.dry_run):
            autotune = _read_json(Path(args.delta_cutoff_autotune_output_json))
            effective_min_score_delta = float(((autotune.get("metrics") or {}).get("applied_min_score_delta")) or effective_min_score_delta)

        cmd_delta_governance = [
            py,
            str(root / "scripts" / "core" / "build_canon_singularity_delta_cutoff_governance_gate_v1.py"),
            "--history-jsonl",
            str(args.delta_cutoff_history_jsonl),
            "--window",
            str(int(args.delta_governance_window)),
            "--min-window-size",
            str(int(args.delta_governance_min_window_size)),
            "--min-apply-rate",
            str(float(args.delta_governance_min_apply_rate)),
            "--max-hold-streak",
            str(int(args.delta_governance_max_hold_streak)),
            "--output-json",
            str(args.delta_cutoff_governance_output_json),
        ]
        rc_delta_governance = _run(cmd_delta_governance, dry_run=bool(args.dry_run))
        if rc_delta_governance != 0:
            return rc_delta_governance
        if bool(args.enforce_delta_governance) and (not bool(args.dry_run)):
            delta_gov = _read_json(Path(args.delta_cutoff_governance_output_json))
            if str(delta_gov.get("status") or "") != "pass":
                print("FAIL: delta cutoff governance enforcement failed", file=sys.stderr)
                return 1

    cmd_insight_delta = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_insight_delta_summary_v1.py"),
        "--history-jsonl",
        str(args.insight_history_jsonl),
        "--min-score-delta",
        str(float(effective_min_score_delta)),
        "--output-json",
        str(args.insight_delta_output_json),
    ]
    if args.insight_delta_min_score_bull_pump is not None:
        cmd_insight_delta += ["--min-score-delta-bull-pump", str(float(args.insight_delta_min_score_bull_pump))]
    if args.insight_delta_min_score_sideways_accumulation is not None:
        cmd_insight_delta += [
            "--min-score-delta-sideways-accumulation",
            str(float(args.insight_delta_min_score_sideways_accumulation)),
        ]
    if args.insight_delta_min_score_bear_trend is not None:
        cmd_insight_delta += ["--min-score-delta-bear-trend", str(float(args.insight_delta_min_score_bear_trend))]
    if args.insight_delta_min_score_capitulation is not None:
        cmd_insight_delta += ["--min-score-delta-capitulation", str(float(args.insight_delta_min_score_capitulation))]
    cmd_insight_explain = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_insight_explainability_v1.py"),
        "--insight-json",
        str(args.insight_output_json),
        "--output-json",
        str(args.insight_explainability_output_json),
    ]
    cmd_insight_explain_gate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_insight_explainability_v1.py"),
        "--input-json",
        str(args.insight_explainability_output_json),
        "--output-json",
        str(args.insight_explainability_gate_output_json),
    ]
    cmd_insight_explain_benchmark_gate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_insight_explainability_benchmark_v1.py"),
        "--input-json",
        str(args.insight_explainability_output_json),
        "--benchmark-jsonl",
        str(args.insight_explainability_benchmark_jsonl),
        "--min-coverage-rate",
        str(float(args.insight_explainability_benchmark_min_coverage)),
        "--min-driver-accuracy",
        str(float(args.insight_explainability_benchmark_min_driver_accuracy)),
        "--min-regime-accuracy",
        str(float(args.insight_explainability_benchmark_min_regime_accuracy)),
        "--min-reviewed-count",
        str(int(args.insight_explainability_benchmark_min_reviewed_count)),
        "--output-json",
        str(args.insight_explainability_benchmark_gate_output_json),
    ]
    cmd_insight_explain_benchmark_seed = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_insight_explainability_benchmark_cohort_v1.py"),
        "--explainability-json",
        str(args.insight_explainability_output_json),
        "--output-jsonl",
        str(args.insight_explainability_benchmark_jsonl),
        "--top-n",
        str(int(args.insight_explainability_benchmark_top_n)),
        "--append-missing-only",
    ]
    if bool(args.require_explainability_benchmark):
        cmd_insight_explain_benchmark_gate.append("--require-benchmark")
    cmd_insight_slice_stability = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_insight_slice_stability_v1.py"),
        "--history-jsonl",
        str(args.insight_history_jsonl),
        "--window",
        str(int(args.insight_slice_stability_window)),
        "--output-json",
        str(args.insight_slice_stability_output_json),
    ]
    cmd_insight_slice_stability_gate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_insight_slice_stability_v1.py"),
        "--input-json",
        str(args.insight_slice_stability_output_json),
        "--max-slice-change-count",
        str(int(args.insight_max_slice_change_count)),
        "--output-json",
        str(args.insight_slice_stability_gate_output_json),
    ]
    cmd_weekly_brief = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_weekly_brief_v1.py"),
        "--insight-history-jsonl",
        str(args.insight_history_jsonl),
        "--gate-history-jsonl",
        str(args.quality_gate_history_jsonl),
        "--health-summary-json",
        str(args.quality_gate_health_summary_json),
        "--slice-stability-json",
        str(args.insight_slice_stability_output_json),
        "--window",
        str(int(args.weekly_brief_window)),
        "--output-json",
        str(args.weekly_brief_output_json),
        "--output-md",
        str(args.weekly_brief_output_md),
    ]
    cmd_weekly_brief_gate = [
        py,
        str(root / "scripts" / "core" / "validate_canon_singularity_weekly_brief_v1.py"),
        "--input-json",
        str(args.weekly_brief_output_json),
        "--output-json",
        str(args.weekly_brief_gate_output_json),
    ]
    cmd_weekly_false_alert = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_weekly_false_alert_review_v1.py"),
        "--weekly-brief-json",
        str(args.weekly_brief_output_json),
        "--weekly-brief-gate-json",
        str(args.weekly_brief_gate_output_json),
        "--health-summary-json",
        str(args.quality_gate_health_summary_json),
        "--output-json",
        str(args.weekly_false_alert_review_output_json),
    ]
    cmd_consistency = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_consistency_check_v1.py"),
        "--gate-history-jsonl",
        str(args.quality_gate_history_jsonl),
        "--insight-history-jsonl",
        str(args.insight_history_jsonl),
        "--health-policy-json",
        str(args.quality_gate_policy_output_json),
        "--insight-gate-json",
        str(args.insight_quality_gate_output_json),
        "--insight-delta-json",
        str(args.insight_delta_output_json),
        "--window",
        str(int(args.consistency_window)),
        "--output-json",
        str(args.operational_consistency_output_json),
    ]
    cmd_promotion_gate = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_promotion_gate_v1.py"),
        "--health-summary-json",
        str(args.quality_gate_health_summary_json),
        "--health-policy-json",
        str(args.quality_gate_policy_output_json),
        "--weekly-brief-gate-json",
        str(args.weekly_brief_gate_output_json),
        "--weekly-false-alert-json",
        str(args.weekly_false_alert_review_output_json),
        "--consistency-check-json",
        str(args.operational_consistency_output_json),
        "--insight-delta-json",
        str(args.insight_delta_output_json),
        "--required-health-level",
        str(args.promotion_required_health_level),
        "--max-false-alert-flags",
        str(int(args.promotion_max_false_alert_flags)),
        "--max-delta-changed-count",
        str(int(args.promotion_max_delta_changed_count)),
        "--history-jsonl",
        str(args.promotion_gate_history_jsonl),
        "--promotion-window",
        str(int(args.promotion_window)),
        "--min-promotion-pass-rate",
        str(float(args.promotion_min_pass_rate)),
        "--output-json",
        str(args.promotion_gate_output_json),
    ]
    cmd_promotion_dashboard = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_promotion_dashboard_v1.py"),
        "--health-summary-json",
        str(args.quality_gate_health_summary_json),
        "--health-policy-json",
        str(args.quality_gate_policy_output_json),
        "--weekly-brief-gate-json",
        str(args.weekly_brief_gate_output_json),
        "--weekly-false-alert-json",
        str(args.weekly_false_alert_review_output_json),
        "--consistency-check-json",
        str(args.operational_consistency_output_json),
        "--promotion-gate-json",
        str(args.promotion_gate_output_json),
        "--output-json",
        str(args.promotion_dashboard_output_json),
        "--output-md",
        str(args.promotion_dashboard_output_md),
    ]
    cmd_promotion_alert = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_promotion_alert_v1.py"),
        "--promotion-gate-json",
        str(args.promotion_gate_output_json),
        "--promotion-dashboard-json",
        str(args.promotion_dashboard_output_json),
        "--output-json",
        str(args.promotion_alert_output_json),
        "--output-md",
        str(args.promotion_alert_output_md),
        "--history-jsonl",
        str(args.promotion_alert_history_jsonl),
    ]
    cmd_promotion_readiness = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_promotion_readiness_report_v1.py"),
        "--promotion-history-jsonl",
        str(args.promotion_gate_history_jsonl),
        "--alert-history-jsonl",
        str(args.promotion_alert_history_jsonl),
        "--window-short",
        str(int(args.promotion_window)),
        "--window-long",
        str(int(args.promotion_window_long)),
        "--short-min-pass-rate",
        str(float(args.promotion_min_pass_rate)),
        "--long-min-pass-rate",
        str(float(args.promotion_long_min_pass_rate)),
        "--output-json",
        str(args.promotion_readiness_output_json),
        "--output-md",
        str(args.promotion_readiness_output_md),
    ]
    cmd_promotion_go_no_go = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_promotion_go_no_go_v1.py"),
        "--promotion-gate-json",
        str(args.promotion_gate_output_json),
        "--day7-checkpoint-json",
        str(args.day7_checkpoint_output_json),
        "--freeze-v2-stability-gate-json",
        str(args.strict_baseline_freeze_v2_stability_gate_output_json),
        "--delta-governance-json",
        str(args.delta_cutoff_governance_output_json),
        "--output-json",
        str(args.promotion_go_no_go_output_json),
        "--output-md",
        str(args.promotion_go_no_go_output_md),
    ]
    cmd_regime_calibration = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_regime_calibration_round_v1.py"),
        "--insight-delta-json",
        str(args.insight_delta_output_json),
        "--insight-json",
        str(args.insight_output_json),
        "--output-json",
        str(args.regime_calibration_output_json),
    ]
    cmd_strict_freeze_v2_rollover = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_strict_baseline_freeze_v2_rollover_v1.py"),
        "--freeze-v1-json",
        str(args.strict_baseline_freeze_v1_json),
        "--day7-checkpoint-json",
        str(args.day7_checkpoint_output_json),
        "--quality-gate-policy-json",
        str(args.quality_gate_policy_output_json),
        "--promotion-gate-json",
        str(args.promotion_gate_output_json),
        "--explainability-benchmark-gate-json",
        str(args.insight_explainability_benchmark_gate_output_json),
        "--delta-governance-json",
        str(args.delta_cutoff_governance_output_json),
        "--health-max-fail-count",
        str(int(args.health_max_fail_count)),
        "--health-min-pass-rate",
        str(float(args.health_min_pass_rate)),
        "--insight-delta-min-score",
        str(float(args.insight_delta_min_score)),
        "--delta-governance-min-apply-rate",
        str(float(args.delta_governance_min_apply_rate)),
        "--output-v2-json",
        str(args.strict_baseline_freeze_v2_output_json),
        "--output-v2-md",
        str(args.strict_baseline_freeze_v2_output_md),
        "--output-rollover-json",
        str(args.strict_baseline_freeze_v2_rollover_output_json),
        "--output-rollover-md",
        str(args.strict_baseline_freeze_v2_rollover_output_md),
        "--output-diff-json",
        str(args.strict_baseline_freeze_diff_v2_from_v1_output_json),
        "--output-diff-md",
        str(args.strict_baseline_freeze_diff_v2_from_v1_output_md),
        "--history-jsonl",
        str(args.strict_baseline_freeze_v2_rollover_history_jsonl),
    ]
    if bool(args.require_explainability_benchmark):
        cmd_strict_freeze_v2_rollover.append("--require-explainability-benchmark")
    cmd_strict_freeze_v2_stability_gate = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_strict_baseline_freeze_v2_stability_gate_v1.py"),
        "--history-jsonl",
        str(args.strict_baseline_freeze_v2_rollover_history_jsonl),
        "--window",
        str(int(args.strict_baseline_freeze_v2_stability_window)),
        "--min-window-size",
        str(int(args.strict_baseline_freeze_v2_stability_min_window_size)),
        "--min-frozen-rate",
        str(float(args.strict_baseline_freeze_v2_stability_min_frozen_rate)),
        "--output-json",
        str(args.strict_baseline_freeze_v2_stability_gate_output_json),
        "--output-md",
        str(args.strict_baseline_freeze_v2_stability_gate_output_md),
    ]
    cmd_strict_freeze_vfinal = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_strict_baseline_freeze_vfinal_v1.py"),
        "--promotion-go-no-go-json",
        str(args.promotion_go_no_go_output_json),
        "--promotion-gate-json",
        str(args.promotion_gate_output_json),
        "--day7-checkpoint-json",
        str(args.day7_checkpoint_output_json),
        "--freeze-v2-stability-gate-json",
        str(args.strict_baseline_freeze_v2_stability_gate_output_json),
        "--delta-governance-json",
        str(args.delta_cutoff_governance_output_json),
        "--strict-health-max-fail-count",
        "0",
        "--strict-health-min-pass-rate",
        "1.0",
        "--strict-insight-delta-min-score",
        "0.001",
        "--strict-delta-governance-min-apply-rate",
        "0.0",
        "--strict-delta-governance-max-hold-streak",
        "20",
        "--strict-require-explainability-benchmark",
        "--balanced-health-max-fail-count",
        str(int(args.health_max_fail_count)),
        "--balanced-health-min-pass-rate",
        str(float(args.health_min_pass_rate)),
        "--balanced-insight-delta-min-score",
        str(float(args.insight_delta_min_score)),
        "--balanced-delta-governance-min-apply-rate",
        str(float(args.delta_governance_min_apply_rate)),
        "--balanced-delta-governance-max-hold-streak",
        str(int(args.delta_governance_max_hold_streak)),
        "--output-json",
        str(args.strict_baseline_freeze_vfinal_output_json),
        "--output-md",
        str(args.strict_baseline_freeze_vfinal_output_md),
    ]
    cmd_strict_freeze_generation_diff = [
        py,
        str(root / "scripts" / "core" / "build_canon_singularity_strict_baseline_freeze_generation_diff_vfinal_v1.py"),
        "--freeze-v1-json",
        str(args.strict_baseline_freeze_v1_json),
        "--freeze-v2-json",
        str(args.strict_baseline_freeze_v2_output_json),
        "--freeze-vfinal-json",
        str(args.strict_baseline_freeze_vfinal_output_json),
        "--output-json",
        str(args.strict_baseline_freeze_generation_diff_output_json),
        "--output-md",
        str(args.strict_baseline_freeze_generation_diff_output_md),
    ]

    cmds = [cmd_report, cmd_balanced, cmd_summary]
    rc_validate = 0

    for cmd in cmds:
        rc = _run(cmd, dry_run=bool(args.dry_run))
        if rc != 0:
            return rc
    if not args.skip_validate:
        rc_validate = _run(cmd_validate, dry_run=bool(args.dry_run))
        rc_health = _run(cmd_health_summary, dry_run=bool(args.dry_run))
        if rc_validate != 0:
            return rc_validate
        if rc_health != 0:
            return rc_health
        if bool(args.enforce_health):
            rc_enforce = _run(cmd_enforce_health, dry_run=bool(args.dry_run))
            if rc_enforce != 0:
                return rc_enforce
    if not args.skip_insight:
        rc_insight = _run(cmd_insight, dry_run=bool(args.dry_run))
        if rc_insight != 0:
            return rc_insight
        rc_insight_gate = _run(cmd_insight_gate, dry_run=bool(args.dry_run))
        if rc_insight_gate != 0:
            return rc_insight_gate
        rc_insight_delta = _run(cmd_insight_delta, dry_run=bool(args.dry_run))
        if rc_insight_delta != 0:
            return rc_insight_delta
        rc_explain = _run(cmd_insight_explain, dry_run=bool(args.dry_run))
        if rc_explain != 0:
            return rc_explain
        rc_explain_gate = _run(cmd_insight_explain_gate, dry_run=bool(args.dry_run))
        if rc_explain_gate != 0:
            return rc_explain_gate
        rc_explain_benchmark_seed = _run(cmd_insight_explain_benchmark_seed, dry_run=bool(args.dry_run))
        if rc_explain_benchmark_seed != 0:
            return rc_explain_benchmark_seed
        rc_explain_benchmark = _run(cmd_insight_explain_benchmark_gate, dry_run=bool(args.dry_run))
        if rc_explain_benchmark != 0:
            return rc_explain_benchmark
        rc_slice = _run(cmd_insight_slice_stability, dry_run=bool(args.dry_run))
        if rc_slice != 0:
            return rc_slice
        rc_slice_gate = _run(cmd_insight_slice_stability_gate, dry_run=bool(args.dry_run))
        if rc_slice_gate != 0:
            return rc_slice_gate
        rc_weekly = _run(cmd_weekly_brief, dry_run=bool(args.dry_run))
        if rc_weekly != 0:
            return rc_weekly
        rc_weekly_gate = _run(cmd_weekly_brief_gate, dry_run=bool(args.dry_run))
        if rc_weekly_gate != 0:
            return rc_weekly_gate
        rc_weekly_review = _run(cmd_weekly_false_alert, dry_run=bool(args.dry_run))
        if rc_weekly_review != 0:
            return rc_weekly_review
        rc_consistency = _run(cmd_consistency, dry_run=bool(args.dry_run))
        if rc_consistency != 0:
            return rc_consistency
        rc_promotion = _run(cmd_promotion_gate, dry_run=bool(args.dry_run))
        if rc_promotion != 0:
            return rc_promotion
        rc_dashboard = _run(cmd_promotion_dashboard, dry_run=bool(args.dry_run))
        if rc_dashboard != 0:
            return rc_dashboard
        rc_alert = _run(cmd_promotion_alert, dry_run=bool(args.dry_run))
        if rc_alert != 0:
            return rc_alert
        rc_readiness = _run(cmd_promotion_readiness, dry_run=bool(args.dry_run))
        if rc_readiness != 0:
            return rc_readiness
        rc_calib = _run(cmd_regime_calibration, dry_run=bool(args.dry_run))
        if rc_calib != 0:
            return rc_calib
        rc_rollover = _run(cmd_strict_freeze_v2_rollover, dry_run=bool(args.dry_run))
        if rc_rollover != 0:
            return rc_rollover
        rc_stability = _run(cmd_strict_freeze_v2_stability_gate, dry_run=bool(args.dry_run))
        if rc_stability != 0:
            return rc_stability
        rc_go_no_go = _run(cmd_promotion_go_no_go, dry_run=bool(args.dry_run))
        if rc_go_no_go != 0:
            return rc_go_no_go
        rc_vfinal = _run(cmd_strict_freeze_vfinal, dry_run=bool(args.dry_run))
        if rc_vfinal != 0:
            return rc_vfinal
        rc_gen_diff = _run(cmd_strict_freeze_generation_diff, dry_run=bool(args.dry_run))
        if rc_gen_diff != 0:
            return rc_gen_diff
        if bool(args.enforce_promotion) and (not bool(args.dry_run)):
            promo = json.loads(Path(args.promotion_gate_output_json).read_text(encoding="utf-8"))
            if str(promo.get("status") or "") != "pass":
                print("FAIL: promotion gate enforcement failed", file=sys.stderr)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

