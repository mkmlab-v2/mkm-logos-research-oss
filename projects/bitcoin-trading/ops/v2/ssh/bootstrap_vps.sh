#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash ops/v2/ssh/bootstrap_vps.sh /opt/bitcoin-trading

TARGET_DIR="${1:-/opt/bitcoin-trading}"
REPO_URL="${REPO_URL:-}"

echo "[bootstrap] target_dir=${TARGET_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[bootstrap] python3 is required." >&2
  exit 2
fi
if ! command -v pm2 >/dev/null 2>&1; then
  echo "[bootstrap] pm2 not found. installing globally..."
  npm install -g pm2
fi

if [[ ! -d "${TARGET_DIR}/.git" ]]; then
  if [[ -z "${REPO_URL}" ]]; then
    echo "[bootstrap] ${TARGET_DIR} is not a git repo and REPO_URL is empty." >&2
    echo "[bootstrap] export REPO_URL=<git-url> and rerun." >&2
    exit 2
  fi
  mkdir -p "$(dirname "${TARGET_DIR}")"
  git clone "${REPO_URL}" "${TARGET_DIR}"
fi

cd "${TARGET_DIR}"
git pull --ff-only || true

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p memory/v2/ops memory/v2/briefs memory/v2/external_memory

echo "[bootstrap] done. next:"
echo "  source ${TARGET_DIR}/.venv/bin/activate"
echo "  pm2 start ops/v2/ssh/ecosystem.ssh.config.cjs"
echo "  pm2 save && pm2 startup"
