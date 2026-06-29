#!/usr/bin/env bash
# WSL2: Nemotron 30B QLoRA smoke — uses uv venv at .venv-wsl-nemotron (torch cu128 + sm_120).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PY:-$ROOT/.venv-wsl-nemotron/bin/python}"
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONUNBUFFERED=1
export MKM_KAGGLE_TRAIN_PROFILE=nemotron
export UV_LINK_MODE=copy

export HF_HOME="${HF_HOME:-$ROOT/storage/hf_cache/nemotron_wsl}"
export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
export TRANSFORMERS_CACHE="${HF_HOME}/transformers"
mkdir -p "$HF_HOME"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^HF_TOKEN=' .env | sed 's/\r$//')
  set +a
fi

if ! "$PY" -c "import mamba_ssm" 2>/dev/null; then
  echo "[run] mamba_ssm missing — installing wheels ..."
  bash "$ROOT/scripts/run_nemotron_wsl_install_mamba_v1.sh" "$PY"
fi

TRAIN="$ROOT/data/kaggle/nvidia-nemotron-model-reasoning-challenge/kaggle_train/nemotron_qlora_train_v1.py"
LOG="${LOG:-$ROOT/reports/nemotron_wsl_smoke_latest.log}"
mkdir -p "$(dirname "$LOG")"

echo "[run] python=$PY log=$LOG hf_home=$HF_HOME"
"$PY" "$TRAIN" \
  --smoke \
  --base-model "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16" \
  --smoke-rows 64 \
  --smoke-steps 20 \
  2>&1 | tee "$LOG"

echo "[OK] WSL nemotron smoke — report: $ROOT/reports/kaggle_nemotron_kaggle_train_latest.json"
