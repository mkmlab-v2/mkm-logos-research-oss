#!/usr/bin/env bash
# RunPod pod: bootstrap deps + Nemotron 30B QLoRA full train (research_only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "=== RunPod Nemotron FULL train (all-in-one) ==="
echo "root=$ROOT"
bash "$ROOT/scripts/run_nemotron_cloud_bootstrap_v1.sh"
bash "$ROOT/scripts/run_nemotron_cloud_gpu_full_v1.sh"
echo "=== done — pull reports/kaggle_nemotron_kaggle_train_full_latest.json ==="
