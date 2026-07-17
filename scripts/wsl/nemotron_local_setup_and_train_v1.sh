#!/usr/bin/env bash
# Nemotron QLoRA — WSL2 + local NVIDIA GPU (RTX). No Kaggle.
set -euo pipefail

ROOT="/mnt/c/workspace"
VENV="$ROOT/.venv-wsl-nemotron"
TRAIN="$ROOT/data/nvidia/nemotron-local/nemotron_qlora_train_v1.py"

cd "$ROOT"

if [[ $# -eq 0 ]]; then
  set -- --dry-run --limit 8
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[ERROR] nvidia-smi missing in WSL. Install WSL CUDA driver / restart WSL." >&2
  exit 1
fi

if [[ ! -d "$VENV" ]]; then
  echo "[setup] creating venv $VENV"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

pip install -q -U pip wheel

if ! python -c "import pandas" 2>/dev/null; then
  echo "[setup] installing pandas (dry-run CSV parse)..."
  pip install -q pandas
fi

echo "[setup] pinning PyTorch 2.10.0+cu128 (mamba wheel ABI match)..."
pip install -q "torch==2.10.0" "torchvision==0.25.0" "torchaudio==2.10.0" \
  --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; assert torch.cuda.is_available(), 'CUDA not visible in WSL'; print('[setup] torch', torch.__version__, 'cuda ok')"

if [[ " $* " == *" --smoke "* ]] && [[ -z "${HF_TOKEN:-}" && -z "${HUGGING_FACE_HUB_TOKEN:-}" ]]; then
  echo "[WARN] HF_TOKEN unset — gated base model download may fail in WSL." >&2
  echo "[WARN] Export HF_TOKEN in WSL before -Smoke (see nvidia_nemotron_local_dev_policy_v1.json)." >&2
fi

export ACCELERATE_BYPASS_DEVICE_MAP=true

echo "[run] python $TRAIN $*"
python "$TRAIN" "$@"
