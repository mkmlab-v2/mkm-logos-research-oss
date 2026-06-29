#!/usr/bin/env bash
# WSL2: install Nemotron QLoRA smoke deps (trl, bitsandbytes, mamba-ssm).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
import torch
print(f"[setup] torch={torch.__version__} cuda={torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"[setup] gpu={torch.cuda.get_device_name(0)}")
PY

python3 -m pip install -q --upgrade pip
python3 -m pip install -q trl bitsandbytes accelerate huggingface_hub

# mamba-ssm: try PyPI wheel first; fall back to GitHub prebuilt like Kaggle script.
if ! python3 -c "import mamba_ssm" 2>/dev/null; then
  echo "[setup] installing causal-conv1d + mamba-ssm ..."
  if ! python3 -m pip install -q causal-conv1d mamba-ssm; then
    echo "[setup] PyPI mamba failed — trying prebuilt wheels ..."
    PY_TAG="cp$(python3 -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
    TORCH_TAG="$(python3 -c 'import torch; v=torch.__version__.split("+")[0]; p=v.split("."); print(f"torch{p[0]}{p[1]}")')"
    ABI="$(python3 -c 'import torch; print(1 if torch._C._GLIBCXX_USE_CXX11_ABI else 0)')"
    WHEEL_DIR="/tmp/mamba_wheels"
    mkdir -p "$WHEEL_DIR"
    BASE="https://github.com/state-spaces/mamba/releases/download/v2.3.2.post1"
    CAUSAL="causal_conv1d-1.6.2.post1+${TORCH_TAG}cxx11abi${ABI}-${PY_TAG}-${PY_TAG}-linux_x86_64.whl"
    MAMBA="mamba_ssm-2.3.2.post1+${TORCH_TAG}cxx11abi${ABI}-${PY_TAG}-${PY_TAG}-linux_x86_64.whl"
    curl -fsSL -o "$WHEEL_DIR/$CAUSAL" "$BASE/$CAUSAL" || true
    curl -fsSL -o "$WHEEL_DIR/$MAMBA" "$BASE/$MAMBA" || true
    python3 -m pip install -q "$WHEEL_DIR"/*.whl || {
      echo "[setup] ERROR: mamba-ssm install failed. torch_tag=$TORCH_TAG abi=$ABI py=$PY_TAG"
      exit 1
    }
  fi
fi

python3 - <<'PY'
import importlib
for m in ("trl", "bitsandbytes", "mamba_ssm", "peft", "transformers"):
    importlib.import_module(m)
    print(f"[setup] {m} OK")
PY
echo "[setup] WSL deps ready"
