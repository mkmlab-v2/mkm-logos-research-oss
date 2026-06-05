#!/usr/bin/env bash
# RunPod pod: bootstrap deps + Nemotron 30B QLoRA smoke (research_only).
# Prereqs: L40S/A100 40GB+ recommended, HF_TOKEN env, repo at /workspace.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "=== RunPod Nemotron smoke (all-in-one) ==="
echo "root=$ROOT"
bash "$ROOT/scripts/run_nemotron_cloud_bootstrap_v1.sh"
bash "$ROOT/scripts/run_nemotron_cloud_gpu_smoke_v1.sh"
echo "=== done — pull reports/kaggle_nemotron_kaggle_train_latest.json ==="
