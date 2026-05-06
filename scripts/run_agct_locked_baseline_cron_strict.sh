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
