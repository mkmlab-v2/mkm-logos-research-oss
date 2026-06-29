#!/usr/bin/env bash
# Install NVIDIA NGC CLI to ~/.local/ngc-cli (no sudo). Idempotent.
set -euo pipefail

INSTALL_ROOT="$HOME/.local/ngc-cli"
BIN="$INSTALL_ROOT/ngc-cli/ngc"
NGC_VERSION="4.19.0"

if [[ -x "$BIN" ]]; then
  "$BIN" --version
  exit 0
fi

mkdir -p "$HOME/.local/bin"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

wget -q --content-disposition \
  "https://api.ngc.nvidia.com/v2/resources/nvidia/ngc-apps/ngc_cli/versions/${NGC_VERSION}/files/ngccli_linux.zip" \
  -O ngccli_linux.zip

python3 - <<'PY'
import zipfile
zipfile.ZipFile("ngccli_linux.zip").extractall(".")
PY

rm -rf "$INSTALL_ROOT"
mkdir -p "$INSTALL_ROOT"
mv ngc-cli "$INSTALL_ROOT/"

chmod +x "$BIN"
ln -sf "$BIN" "$HOME/.local/bin/ngc"

if ! grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

"$BIN" --version
echo "[OK] NGC CLI ${NGC_VERSION} -> $BIN"
