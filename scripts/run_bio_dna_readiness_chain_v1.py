#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.79, K:0.66, M:0.4}
# Balance: 89
# Purpose: Execute DNA readiness chain end-to-end from genotype normalization to readiness gate.
# Keywords: bio, dna, readiness, chain, promotion, pipeline
"""Run bio DNA readiness chain."""

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
    ap = argparse.ArgumentParser(description="Run bio DNA readiness chain.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-input-csv", type=Path, required=True)
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
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
    ap.add_argument(
        "--threshold-sweep-report",
        type=Path,
        default=Path("reports/bio_dna_promotion_threshold_sweep_v1_latest.json"),
    )
    ap.add_argument("--min-coverage-ratio", type=float, default=0.30)
    ap.add_argument("--min-target-rows", type=int, default=1)
    ap.add_argument("--min-match-rows", type=int, default=1)
    ap.add_argument("--focus-sample-id", type=str, default="")
    ap.add_argument("--min-focus-match-ratio", type=float, default=None)
    ap.add_argument("--run-threshold-sweep", action="store_true")
    ap.add_argument("--strict-readiness", action="store_true")
    ns = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    s_norm = repo_root / "scripts" / "normalize_bio_genotype_long_v1.py"
    s_overlap = repo_root / "scripts" / "check_bio_genotype_paper_snp_overlap_v1.py"
    s_ready = repo_root / "scripts" / "build_bio_dna_promotion_readiness_v1.py"
    s_sweep = repo_root / "scripts" / "run_bio_dna_promotion_threshold_sweep_v1.py"

    _run(
        "normalize_genotype_long",
        [
            str(s_norm),
            "--input-csv",
            str(ns.genotype_input_csv),
            "--output-csv",
            str(ns.normalized_genotype_csv),
            "--output-report",
            str(ns.normalized_report),
        ],
    )
    _run(
        "genotype_paper_snp_overlap",
        [
            str(s_overlap),
            "--cohort-csv",
            str(ns.cohort_csv),
            "--genotype-csv",
            str(ns.normalized_genotype_csv),
            "--output-csv",
            str(ns.overlap_csv),
            "--output-report",
            str(ns.overlap_report),
        ],
    )
    ready_args = [
        str(s_ready),
        "--mapping-coverage-report",
        str(ns.mapping_coverage_report),
        "--overlap-report",
        str(ns.overlap_report),
        "--min-coverage-ratio",
        str(ns.min_coverage_ratio),
        "--min-target-rows",
        str(ns.min_target_rows),
        "--min-match-rows",
        str(ns.min_match_rows),
        "--output-json",
        str(ns.readiness_report),
    ]
    if ns.strict_readiness:
        ready_args.append("--strict")
    if ns.focus_sample_id:
        ready_args.extend(["--overlap-csv", str(ns.overlap_csv)])
        ready_args.extend(["--focus-sample-id", ns.focus_sample_id])
        if ns.min_focus_match_ratio is not None:
            ready_args.extend(["--min-focus-match-ratio", str(ns.min_focus_match_ratio)])
    _run("build_readiness", ready_args)

    if ns.run_threshold_sweep:
        _run(
            "threshold_sweep",
            [
                str(s_sweep),
                "--mapping-coverage-report",
                str(ns.mapping_coverage_report),
                "--overlap-report",
                str(ns.overlap_report),
                "--output-json",
                str(ns.threshold_sweep_report),
            ],
        )

    print("OK: run_bio_dna_readiness_chain_v1 completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
