#!/usr/bin/env bash
# Cloud GPU smoke (RunPod / Lambda / Vast / Azure VM after quota): Nemotron 30B QLoRA.
# Prereqs: 24GB+ VRAM (40GB+ recommended), ~80GB free disk, HF_TOKEN in env.
# Usage:
#   export HF_TOKEN=...
#   bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONUNBUFFERED=1
export MKM_KAGGLE_TRAIN_PROFILE=nemotron
export HF_HOME="${HF_HOME:-$ROOT/storage/hf_cache/nemotron_cloud}"
export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
export TRANSFORMERS_CACHE="${HF_HOME}/transformers"
mkdir -p "$HF_HOME"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^HF_TOKEN=' .env | sed 's/\r$//')
  set +a
fi

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "[FAIL] HF_TOKEN required (export or .env)" >&2
  exit 2
fi

PY="${PY:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python
fi

"$PY" - <<'PYCHECK'
import shutil
import sys

try:
    import torch
except ImportError:
    print("[FAIL] torch not installed — see Run-NemotronCloudGpuSmoke_v1.ps1 checklist", file=sys.stderr)
    sys.exit(3)

if not torch.cuda.is_available():
    print("[FAIL] CUDA not available on this host", file=sys.stderr)
    sys.exit(4)

n = torch.cuda.device_count()
total_gb = sum(torch.cuda.get_device_properties(i).total_memory for i in range(n)) / (1024**3)
print(f"[check] cuda devices={n} total_vram={total_gb:.1f}GB")
if total_gb < 20:
    print("[FAIL] need ~20GB+ total VRAM for Nemotron 30B 4bit QLoRA", file=sys.stderr)
    sys.exit(5)

free = shutil.disk_usage(".").free / (1024**3)
print(f"[check] disk_free={free:.1f}GB (cwd={__import__('os').getcwd()})")
if free < 70:
    print("[WARN] disk <70GB — first run downloads ~63GB BF16 weights", file=sys.stderr)
PYCHECK

TRAIN="$ROOT/data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/nemotron_qlora_train_v1.py"
LOG="${LOG:-$ROOT/reports/nemotron_cloud_gpu_smoke_latest.log}"
mkdir -p "$(dirname "$LOG")"

echo "[run] python=$($PY -V 2>&1) log=$LOG hf_home=$HF_HOME"
"$PY" "$TRAIN" \
  --smoke \
  --base-model "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16" \
  --smoke-rows 64 \
  --smoke-steps 20 \
  2>&1 | tee "$LOG"

echo "[OK] cloud smoke done — report: $ROOT/reports/kaggle_nemotron_kaggle_train_latest.json"
