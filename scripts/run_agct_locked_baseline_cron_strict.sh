#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$WORKSPACE_ROOT"
python3 scripts/run_agct_sigma_locked_baseline_chain_v1.py \
  --repro-trials 5 \
  --repro-batches 1 \
  --h2h-trials 5 \
  --h2h-batches 1 \
  --daily-drift-runs 2 \
  --run-regression-check \
  --strict-regression-check

# Keep stage2 compare artifact in sync for strict runs too.
python3 scripts/build_agct_sasang_stage2_candidate_compare_v1.py
python3 scripts/append_agct_sasang_stage2_compare_history_v1.py
python3 scripts/check_agct_sasang_stage2_promotion_gate_v1.py
python3 scripts/check_agct_sasang_stage2_fasttrack_gate_v1.py
python3 scripts/check_agct_sasang_stage2_d7_checkpoint_v1.py
