#!/usr/bin/env bash
# Cloud GPU full train (RunPod): Nemotron 30B QLoRA — research_only, no --smoke.
# Defaults: 2048 rows · 1 epoch (~3–5h SFT after HF weights cached). Override via env.
#   MKM_NEMOTRON_CLOUD_FULL_LIMIT=0     # all train.csv rows (69k+ — very long)
#   MKM_NEMOTRON_CLOUD_FULL_MAX_STEPS=500
#   MKM_NEMOTRON_CLOUD_FULL_EPOCHS=1
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONUNBUFFERED=1
export MKM_KAGGLE_TRAIN_PROFILE=nemotron
export MKM_KAGGLE_FULL=1
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
    print("[FAIL] torch not installed", file=sys.stderr)
    sys.exit(3)

if not torch.cuda.is_available():
    print("[FAIL] CUDA not available", file=sys.stderr)
    sys.exit(4)

n = torch.cuda.device_count()
total_gb = sum(torch.cuda.get_device_properties(i).total_memory for i in range(n)) / (1024**3)
print(f"[check] cuda devices={n} total_vram={total_gb:.1f}GB")
if total_gb < 20:
    print("[FAIL] need ~20GB+ VRAM for Nemotron 30B 4bit QLoRA", file=sys.stderr)
    sys.exit(5)

free = shutil.disk_usage(".").free / (1024**3)
print(f"[check] disk_free={free:.1f}GB")
if free < 70:
    print("[WARN] disk <70GB — first run downloads ~63GB BF16 weights", file=sys.stderr)
PYCHECK

FULL_LIMIT="${MKM_NEMOTRON_CLOUD_FULL_LIMIT:-2048}"
FULL_EPOCHS="${MKM_NEMOTRON_CLOUD_FULL_EPOCHS:-1}"
FULL_MAX_STEPS="${MKM_NEMOTRON_CLOUD_FULL_MAX_STEPS:-0}"

TRAIN="$ROOT/data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/nemotron_qlora_train_v1.py"
LOG="${LOG:-$ROOT/reports/nemotron_cloud_gpu_full_latest.log}"
REPORT="${REPORT:-$ROOT/reports/kaggle_nemotron_kaggle_train_full_latest.json}"
mkdir -p "$(dirname "$LOG")"

echo "[run] FULL train profile=nemotron base=30B limit=$FULL_LIMIT epochs=$FULL_EPOCHS max_steps=$FULL_MAX_STEPS"
echo "[run] log=$LOG report=$REPORT hf_home=$HF_HOME"

ARGS=(
  --base-model "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
  --epochs "$FULL_EPOCHS"
  --out-report-json "$REPORT"
)
if [[ "$FULL_LIMIT" != "0" ]]; then
  ARGS+=(--limit "$FULL_LIMIT")
fi
if [[ "$FULL_MAX_STEPS" != "0" ]]; then
  ARGS+=(--max-steps "$FULL_MAX_STEPS")
fi

"$PY" "$TRAIN" "${ARGS[@]}" 2>&1 | tee "$LOG"

echo "[OK] cloud full train done — report: $REPORT"
