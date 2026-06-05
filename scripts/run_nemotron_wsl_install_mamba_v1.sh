#!/usr/bin/env bash
# Install prebuilt mamba-ssm wheels (same fallback tags as Kaggle train script).
set -euo pipefail
PY="${1:-/mnt/c/workspace/.venv-wsl-nemotron/bin/python}"
PY_TAG="cp$("$PY" -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')"
PLATFORM="linux_x86_64"
TORCH_TAG="$("$PY" -c 'import torch; v=torch.__version__.split("+")[0]; p=v.split("."); minor=p[1] if len(p)>1 else "0"; print(f"cu12torch{p[0]}.{minor}")')"
ABI_PRIMARY="$("$PY" -c 'import torch; print("TRUE" if torch._C._GLIBCXX_USE_CXX11_ABI else "FALSE")')"
if [[ "$ABI_PRIMARY" == "TRUE" ]]; then ABI_ORDER=("TRUE" "FALSE"); else ABI_ORDER=("FALSE" "TRUE"); fi
FALLBACKS=("$TORCH_TAG" "cu12torch2.10" "cu12torch2.9" "cu12torch2.8" "cu12torch2.7" "cu12torch2.6")
CAUSAL_BASE="https://github.com/Dao-AILab/causal-conv1d/releases/download/v1.6.2.post1"
MAMBA_BASE="https://github.com/state-spaces/mamba/releases/download/v2.3.2.post1"
WHEEL_DIR="/tmp/mamba_wheels_wsl"
mkdir -p "$WHEEL_DIR"

download() {
  local url="$1" dest="$2"
  echo "[mamba] try $url"
  if curl -fsSL -o "$dest" "$url" && [[ -s "$dest" ]]; then
    return 0
  fi
  rm -f "$dest"
  return 1
}

for tt in "${FALLBACKS[@]}"; do
  for abi in "${ABI_ORDER[@]}"; do
    causal_name="causal_conv1d-1.6.2.post1+${tt}cxx11abi${abi}-${PY_TAG}-${PY_TAG}-${PLATFORM}.whl"
    mamba_name="mamba_ssm-2.3.2.post1+${tt}cxx11abi${abi}-${PY_TAG}-${PY_TAG}-${PLATFORM}.whl"
    causal_path="$WHEEL_DIR/$causal_name"
    mamba_path="$WHEEL_DIR/$mamba_name"
    if download "$CAUSAL_BASE/$causal_name" "$causal_path" && download "$MAMBA_BASE/$mamba_name" "$mamba_path"; then
      if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$PY" --no-deps "$causal_path" "$mamba_path"
      else
        "$PY" -m pip install -q --no-deps "$causal_path" "$mamba_path"
      fi
      "$PY" -c "import mamba_ssm; print('[mamba] ok', mamba_ssm.__file__)"
      exit 0
    fi
  done
done
echo "[mamba] ERROR: no matching wheel for torch=$("$PY" -c 'import torch; print(torch.__version__)')"
exit 1
