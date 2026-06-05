#!/usr/bin/env bash
# One-time deps on a fresh RunPod/Lambda PyTorch image (CUDA 12.x).
# Keeps template torch when CUDA works; installs mamba via prebuilt wheels only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PY:-python3}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$ROOT/.pip_cache}"
mkdir -p "$PIP_CACHE_DIR"
"$PY" -m pip install -U pip wheel

need_torch_repair=0
if ! "$PY" -c "import torch; assert torch.cuda.is_available(); torch.zeros(1, device='cuda')" 2>/dev/null; then
  need_torch_repair=1
fi
if "$PY" -c "import torch; import sys; sys.exit(0 if (torch.version.cuda or '').startswith(('12.', '11.')) else 1)" 2>/dev/null; then
  :
else
  need_torch_repair=1
fi

if [[ "$need_torch_repair" -eq 1 ]]; then
  echo "[bootstrap] installing torch 2.10.0+cu128 (mamba prebuilt wheels; CUDA 12.4 driver OK)..."
  "$PY" -m pip install "torch==2.10.0" "torchvision" "torchaudio" \
    --index-url https://download.pytorch.org/whl/cu128
fi

TORCH_PIN="$("$PY" -c "import torch; print(torch.__version__)")"
CUDA_PIN="$("$PY" -c "import torch; print(torch.version.cuda or 'unknown')")"
echo "[bootstrap] torch=$TORCH_PIN cuda=$CUDA_PIN"

CONSTRAINT="$(mktemp)"
printf 'torch==%s\n' "$TORCH_PIN" >"$CONSTRAINT"
export PIP_CONSTRAINT="$CONSTRAINT"
trap 'rm -f "$CONSTRAINT"' EXIT

"$PY" -m pip install \
  "transformers>=4.46" \
  "peft>=0.13" \
  "trl>=0.12" \
  "bitsandbytes>=0.44" \
  "accelerate>=1.0" \
  "datasets>=3.0" \
  "huggingface_hub>=0.26" \
  "psutil" \
  "einops" \
  "sentencepiece" \
  --upgrade-strategy only-if-needed

# peft/trl can pull torch>=2.5 — re-pin template-matched cu124 if CUDA broke.
if ! "$PY" -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
  echo "[bootstrap] CUDA broken after HF stack — force torch 2.10.0+cu128..."
  "$PY" -m pip install "torch==2.10.0" "torchvision" "torchaudio" \
    --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
fi
TORCH_PIN="$("$PY" -c "import torch; print(torch.__version__)")"
echo "[bootstrap] post-hf torch=$TORCH_PIN cuda_avail=$("$PY" -c "import torch; print(torch.cuda.is_available())")"

if ! "$PY" -c "import mamba_ssm" 2>/dev/null; then
  # Prebuilt mamba wheels target torch 2.10+cu128 — template torch 2.4+cu124 passes CUDA smoke but breaks ABI.
  TORCH_MAJOR_MINOR="$("$PY" -c 'import torch; p=torch.__version__.split("+")[0].split("."); print(f"{p[0]}.{p[1]}")')"
  if [[ "$TORCH_MAJOR_MINOR" != "2.10" ]]; then
    echo "[bootstrap] torch=$TORCH_MAJOR_MINOR — upgrading to 2.10.0+cu128 for mamba wheels..."
    "$PY" -m pip install "torch==2.10.0" "torchvision" "torchaudio" \
      --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
  fi
  MAMBA_INSTALL="$ROOT/scripts/run_nemotron_wsl_install_mamba_v1.sh"
  if [[ -f "$MAMBA_INSTALL" ]]; then
    bash "$MAMBA_INSTALL" "$PY"
  else
    echo "[bootstrap][FAIL] missing $MAMBA_INSTALL (Nemotron needs mamba-ssm wheels)" >&2
    exit 1
  fi
fi

echo "[OK] cloud bootstrap — run: bash scripts/run_nemotron_cloud_gpu_smoke_v1.sh"
