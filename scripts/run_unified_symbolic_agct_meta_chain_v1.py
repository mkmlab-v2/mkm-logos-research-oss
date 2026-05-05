#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.92, L:0.9, K:0.73, M:0.5}
# Balance: 91
# Purpose: Run AGCT chain + symbolic shadow + unified meta guard end-to-end.
# Keywords: unified, agct, symbolic, meta, chain, guard
"""Run unified symbolic+AGCT meta chain v1."""

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
    ap = argparse.ArgumentParser(description="Run unified symbolic+AGCT meta chain.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-input-csv", type=Path, required=True)
    ap.add_argument("--mapping-coverage-report", type=Path, required=True)
    ap.add_argument(
        "--symbolic-pairs-jsonl",
        type=Path,
        default=Path("tests/fixtures/symbolic_mapping_demo_pairs_v1.jsonl"),
    )
    ap.add_argument(
        "--symbolic-stream-jsonl",
        type=Path,
        default=Path("tests/fixtures/symbolic_mapping_shadow_stream_v1.jsonl"),
    )
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument("--run-holdout-eval", action="store_true", default=True)
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument("--build-runtime-stub", action="store_true", default=True)
    ap.add_argument("--runtime-enabled", action="store_true")
    ap.add_argument("--enforce-holdout-runtime-guard", action="store_true", default=True)
    ap.add_argument("--min-holdout-n", type=int, default=30)
    ap.add_argument("--min-holdout-accuracy", type=float, default=0.50)
    ap.add_argument("--max-generalization-gap", type=float, default=0.40)
    ap.add_argument("--max-holdout-pvalue", type=float, default=0.20)
    ap.add_argument("--symbolic-max-mean-loss", type=float, default=0.08)
    ap.add_argument("--symbolic-max-drift", type=float, default=0.03)
    ap.add_argument(
        "--agct-runtime-stub-json",
        type=Path,
        default=Path("reports/agct_sasang_size_overlay_runtime_stub_v1_latest.json"),
    )
    ap.add_argument(
        "--symbolic-fit-json",
        type=Path,
        default=Path("reports/symbolic_math_mapping_fit_v1_latest.json"),
    )
    ap.add_argument(
        "--symbolic-shadow-gate-json",
        type=Path,
        default=Path("reports/symbolic_math_mapping_shadow_gate_v1_latest.json"),
    )
    ap.add_argument(
        "--unified-meta-guard-json",
        type=Path,
        default=Path("reports/unified_symbolic_agct_meta_guard_v1_latest.json"),
    )
    ns = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    s_agct = repo_root / "scripts" / "run_agct_sasang_research_chain_v1.py"
    s_precheck = repo_root / "scripts" / "check_unified_meta_chain_readiness_v1.py"
    s_sym_fit = repo_root / "scripts" / "run_symbolic_math_mapping_fit_v1.py"
    s_sym_shadow = repo_root / "scripts" / "run_symbolic_math_mapping_shadow_gate_v1.py"
    s_meta = repo_root / "scripts" / "build_unified_symbolic_agct_meta_guard_v1.py"

    _run(
        "precheck",
        [
            str(s_precheck),
            "--cohort-csv",
            str(ns.cohort_csv),
            "--genotype-input-csv",
            str(ns.genotype_input_csv),
            "--mapping-coverage-report",
            str(ns.mapping_coverage_report),
            "--symbolic-pairs-jsonl",
            str(ns.symbolic_pairs_jsonl),
            "--symbolic-stream-jsonl",
            str(ns.symbolic_stream_jsonl),
            "--holdout-ratio",
            str(ns.holdout_ratio),
            "--min-holdout-n",
            str(ns.min_holdout_n),
        ],
    )

    # A) AGCT chain (with runtime holdout guard)
    agct_args = [
        str(s_agct),
        "--cohort-csv",
        str(ns.cohort_csv),
        "--genotype-input-csv",
        str(ns.genotype_input_csv),
        "--mapping-coverage-report",
        str(ns.mapping_coverage_report),
        "--permutation-repeats",
        str(ns.permutation_repeats),
        "--holdout-ratio",
        str(ns.holdout_ratio),
        "--min-holdout-n",
        str(ns.min_holdout_n),
        "--min-holdout-accuracy",
        str(ns.min_holdout_accuracy),
        "--max-generalization-gap",
        str(ns.max_generalization_gap),
        "--max-holdout-pvalue",
        str(ns.max_holdout_pvalue),
        "--runtime-stub-report",
        str(ns.agct_runtime_stub_json),
    ]
    if ns.run_holdout_eval:
        agct_args.append("--run-holdout-eval")
    if ns.build_runtime_stub:
        agct_args.append("--build-runtime-stub")
    if ns.runtime_enabled:
        agct_args.append("--runtime-enabled")
    if ns.enforce_holdout_runtime_guard:
        agct_args.append("--enforce-holdout-runtime-guard")
    _run("agct_chain", agct_args)

    # B) Symbolic fit
    _run(
        "symbolic_fit",
        [
            str(s_sym_fit),
            "--pairs-jsonl",
            str(ns.symbolic_pairs_jsonl),
            "--out",
            str(ns.symbolic_fit_json),
        ],
    )

    # C) Symbolic shadow gate
    _run(
        "symbolic_shadow_gate",
        [
            str(s_sym_shadow),
            "--fit-json",
            str(ns.symbolic_fit_json),
            "--stream-jsonl",
            str(ns.symbolic_stream_jsonl),
            "--max-mean-loss",
            str(ns.symbolic_max_mean_loss),
            "--max-drift",
            str(ns.symbolic_max_drift),
            "--out",
            str(ns.symbolic_shadow_gate_json),
        ],
    )

    # D) Unified meta guard
    _run(
        "unified_meta_guard",
        [
            str(s_meta),
            "--agct-runtime-stub-json",
            str(ns.agct_runtime_stub_json),
            "--symbolic-shadow-gate-json",
            str(ns.symbolic_shadow_gate_json),
            "--out",
            str(ns.unified_meta_guard_json),
        ],
    )

    print("OK: run_unified_symbolic_agct_meta_chain_v1 completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
