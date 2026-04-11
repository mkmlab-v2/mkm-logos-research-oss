#!/usr/bin/env bash
# Macro prophecy LoRA (Unsloth) — Linux GPU host bootstrap (VPS / cloud / sm_90-capable workstation).
# Usage (repo root on the remote):
#   chmod +x scripts/lora_train_remote_gpu_bootstrap.sh
#   TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124 ./scripts/lora_train_remote_gpu_bootstrap.sh --max-steps 10 --batch-size 1
# Pick TORCH_INDEX_URL from https://pytorch.org/get-started/locally/ for this host's CUDA/driver.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu124}"
VENV_DIR="${VENV_DIR:-.venv_lora_remote}"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found. This script expects an NVIDIA GPU + driver on the host." >&2
  exit 1
fi

PY="${PY:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY="python"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PY" -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip wheel

python -m pip install torch torchvision torchaudio --index-url "$TORCH_INDEX_URL"
python -m pip install datasets trl peft accelerate bitsandbytes sentencepiece protobuf safetensors huggingface_hub packaging
python -m pip install unsloth

python scripts/export_general_prophecy_to_jsonl.py
exec python scripts/train_mkm_prophecy_lora_unsloth.py "$@"
