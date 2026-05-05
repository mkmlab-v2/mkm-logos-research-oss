#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.92, L:0.84, K:0.69, M:0.43}
# Balance: 90
# Purpose: Execute L1->L2->L3 AGCT-Sasang research chain in one command.
# Keywords: bio, dna, sasang, chain, agct, sweep, overlay
"""Run AGCT-Sasang research chain (B-track).

L1: DNA readiness chain
L2: AGCT hypothesis sweep
L3: Size overlay candidate build (research only)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(step: str, args: list[str]) -> None:
    cmd = [sys.executable] + args
    print(f"RUN[{step}] {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"step_failed:{step}:exit={proc.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run AGCT-Sasang research chain.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-input-csv", type=Path, required=True)
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--label-col", type=str, default="expected_parent")
    ap.add_argument("--risk-col", type=str, default="risk_score")
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument(
        "--normalized-genotype-csv",
        type=Path,
        default=Path("tmp/bio_genotype_long_v1.csv"),
    )
    ap.add_argument(
        "--normalized-report",
        type=Path,
        default=Path("reports/bio_genotype_normalize_long_v1_latest.json"),
    )
    ap.add_argument(
        "--overlap-csv",
        type=Path,
        default=Path("tmp/bio_cohort_with_genotype_overlap_v1.csv"),
    )
    ap.add_argument(
        "--overlap-report",
        type=Path,
        default=Path("reports/bio_genotype_paper_snp_overlap_v1_latest.json"),
    )
    ap.add_argument(
        "--readiness-report",
        type=Path,
        default=Path("reports/bio_dna_promotion_readiness_v1_latest.json"),
    )
    ap.add_argument("--min-coverage-ratio", type=float, default=0.30)
    ap.add_argument("--min-target-rows", type=int, default=1)
    ap.add_argument("--min-match-rows", type=int, default=1)
    ap.add_argument("--run-threshold-sweep", action="store_true")
    ap.add_argument(
        "--threshold-sweep-report",
        type=Path,
        default=Path("reports/bio_dna_promotion_threshold_sweep_v1_latest.json"),
    )
    ap.add_argument("--strict-readiness", action="store_true")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--agct-sweep-report",
        type=Path,
        default=Path("reports/agct_sasang_hypothesis_sweep_v1_latest.json"),
    )
    ap.add_argument(
        "--overlay-candidate-report",
        type=Path,
        default=Path("reports/agct_sasang_size_overlay_candidate_v1_latest.json"),
    )
    ap.add_argument(
        "--runtime-stub-report",
        type=Path,
        default=Path("reports/agct_sasang_size_overlay_runtime_stub_v1_latest.json"),
    )
    ap.add_argument("--build-runtime-stub", action="store_true")
    ap.add_argument("--runtime-enabled", action="store_true")
    ap.add_argument("--run-holdout-eval", action="store_true")
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument(
        "--holdout-eval-report",
        type=Path,
        default=Path("reports/agct_sasang_holdout_eval_v1_latest.json"),
    )
    ap.add_argument("--enforce-holdout-runtime-guard", action="store_true")
    ap.add_argument("--min-holdout-accuracy", type=float, default=0.50)
    ap.add_argument("--max-generalization-gap", type=float, default=0.40)
    ap.add_argument("--max-holdout-pvalue", type=float, default=0.20)
    ap.add_argument("--min-holdout-n", type=int, default=30)
    ap.add_argument("--min-best-accuracy", type=float, default=0.45)
    ap.add_argument("--max-permutation-pvalue", type=float, default=0.10)
    ap.add_argument("--max-abs-corr", type=float, default=0.50)
    ap.add_argument("--base-size-multiplier", type=float, default=1.0)
    ns = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    s_readiness_chain = repo_root / "scripts" / "run_bio_dna_readiness_chain_v1.py"
    s_agct_sweep = repo_root / "scripts" / "run_agct_sasang_hypothesis_sweep_v1.py"
    s_overlay = repo_root / "scripts" / "build_agct_sasang_size_overlay_candidate_v1.py"
    s_runtime_stub = repo_root / "scripts" / "build_agct_sasang_size_overlay_runtime_stub_v1.py"
    s_runtime_stub_validate = repo_root / "scripts" / "validate_agct_sasang_size_overlay_runtime_stub_v1.py"
    s_holdout_eval = repo_root / "scripts" / "run_agct_sasang_holdout_eval_v1.py"
    s_holdout_guard = repo_root / "scripts" / "enforce_agct_sasang_holdout_runtime_guard_v1.py"

    # L1
    readiness_args = [
        str(s_readiness_chain),
        "--cohort-csv",
        str(ns.cohort_csv),
        "--genotype-input-csv",
        str(ns.genotype_input_csv),
        "--mapping-coverage-report",
        str(ns.mapping_coverage_report),
        "--normalized-genotype-csv",
        str(ns.normalized_genotype_csv),
        "--normalized-report",
        str(ns.normalized_report),
        "--overlap-csv",
        str(ns.overlap_csv),
        "--overlap-report",
        str(ns.overlap_report),
        "--readiness-report",
        str(ns.readiness_report),
        "--min-coverage-ratio",
        str(ns.min_coverage_ratio),
        "--min-target-rows",
        str(ns.min_target_rows),
        "--min-match-rows",
        str(ns.min_match_rows),
        "--threshold-sweep-report",
        str(ns.threshold_sweep_report),
    ]
    if ns.run_threshold_sweep:
        readiness_args.append("--run-threshold-sweep")
    if ns.strict_readiness:
        readiness_args.append("--strict-readiness")
    _run("l1_dna_readiness_chain", readiness_args)

    # L2
    _run(
        "l2_agct_hypothesis_sweep",
        [
            str(s_agct_sweep),
            "--cohort-csv",
            str(ns.cohort_csv),
            "--genotype-csv",
            str(ns.normalized_genotype_csv),
            "--sample-col",
            str(ns.sample_col),
            "--label-col",
            str(ns.label_col),
            "--risk-col",
            str(ns.risk_col),
            "--genotype-col",
            str(ns.genotype_col),
            "--top-k",
            str(ns.top_k),
            "--permutation-repeats",
            str(ns.permutation_repeats),
            "--seed",
            str(ns.seed),
            "--output-json",
            str(ns.agct_sweep_report),
        ],
    )

    # L3
    _run(
        "l3_size_overlay_candidate",
        [
            str(s_overlay),
            "--readiness-json",
            str(ns.readiness_report),
            "--sweep-json",
            str(ns.agct_sweep_report),
            "--min-best-accuracy",
            str(ns.min_best_accuracy),
            "--max-permutation-pvalue",
            str(ns.max_permutation_pvalue),
            "--max-abs-corr",
            str(ns.max_abs_corr),
            "--base-size-multiplier",
            str(ns.base_size_multiplier),
            "--output-json",
            str(ns.overlay_candidate_report),
        ],
    )

    if ns.run_holdout_eval:
        _run(
            "l3b_holdout_eval",
            [
                str(s_holdout_eval),
                "--cohort-csv",
                str(ns.cohort_csv),
                "--genotype-csv",
                str(ns.normalized_genotype_csv),
                "--sample-col",
                str(ns.sample_col),
                "--label-col",
                str(ns.label_col),
                "--genotype-col",
                str(ns.genotype_col),
                "--holdout-ratio",
                str(ns.holdout_ratio),
                "--seed",
                str(ns.seed),
                "--permutation-repeats",
                str(ns.permutation_repeats),
                "--output-json",
                str(ns.holdout_eval_report),
            ],
        )

    if ns.build_runtime_stub:
        runtime_args = [
            str(s_runtime_stub),
            "--overlay-candidate-json",
            str(ns.overlay_candidate_report),
            "--output-json",
            str(ns.runtime_stub_report),
        ]
        if ns.runtime_enabled:
            runtime_args.append("--runtime-enabled")
        _run("l4_runtime_stub", runtime_args)
        _run(
            "l4_runtime_stub_validate",
            [
                str(s_runtime_stub_validate),
                "--input-json",
                str(ns.runtime_stub_report),
            ],
        )

    if ns.enforce_holdout_runtime_guard:
        if not ns.run_holdout_eval:
            raise RuntimeError("--enforce-holdout-runtime-guard requires --run-holdout-eval")
        if not ns.build_runtime_stub:
            raise RuntimeError("--enforce-holdout-runtime-guard requires --build-runtime-stub")
        _run(
            "l5_holdout_runtime_guard",
            [
                str(s_holdout_guard),
                "--runtime-stub-json",
                str(ns.runtime_stub_report),
                "--holdout-eval-json",
                str(ns.holdout_eval_report),
                "--min-holdout-accuracy",
                str(ns.min_holdout_accuracy),
                "--max-generalization-gap",
                str(ns.max_generalization_gap),
                "--max-holdout-pvalue",
                str(ns.max_holdout_pvalue),
                "--min-holdout-n",
                str(ns.min_holdout_n),
            ],
        )
        _run(
            "l5_runtime_stub_revalidate",
            [
                str(s_runtime_stub_validate),
                "--input-json",
                str(ns.runtime_stub_report),
            ],
        )

    print("OK: run_agct_sasang_research_chain_v1 completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
