#!/usr/bin/env bash
# Install mkm-compression-api-stub.service on Linux (VPS). Requires sudo.
# Usage:
#   export WORKSPACE_ROOT=/opt/workspace   # repo root containing scripts/
#   sudo -E bash scripts/deploy/linux/install_compression_api_stub_systemd.sh
#
# Ops: User=nobody cannot chdir into root-only trees (e.g. /root/...). Use /opt/...
#      or another world-readable path; e.g. sudo chmod -R a+rX "${WORKSPACE_ROOT}".
# Updates: sudo git -C "${WORKSPACE_ROOT}" pull --ff-only origin main && sudo systemctl restart mkm-compression-api-stub
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/workspace}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
SERVICE_SRC="${SCRIPT_DIR}/mkm-compression-api-stub.service"
UNIT_DST="/etc/systemd/system/mkm-compression-api-stub.service"
ENV_DIR="/etc/mkm"
ENV_DST="${ENV_DIR}/compression-api.env"

if [[ ! -f "${SERVICE_SRC}" ]]; then
  echo "Missing ${SERVICE_SRC}" >&2
  exit 1
fi

if [[ ! -d "${WORKSPACE_ROOT}/scripts" ]]; then
  echo "WORKSPACE_ROOT must contain scripts/ (got ${WORKSPACE_ROOT})" >&2
  exit 1
fi

echo "Using WORKSPACE_ROOT=${WORKSPACE_ROOT}"

sudo mkdir -p "${ENV_DIR}"
if [[ ! -f "${ENV_DST}" ]]; then
  echo "Creating ${ENV_DST} from example (edit and chmod 600)."
  sudo cp "${SCRIPT_DIR}/compression-api.env.example" "${ENV_DST}"
fi

# Substitute WorkingDirectory and PYTHONPATH in unit file
tmp_unit="$(mktemp)"
sed -e "s|WorkingDirectory=.*|WorkingDirectory=${WORKSPACE_ROOT}|" \
    -e "s|Environment=PYTHONPATH=.*|Environment=PYTHONPATH=${WORKSPACE_ROOT}|" \
    "${SERVICE_SRC}" >"${tmp_unit}"
sudo cp "${tmp_unit}" "${UNIT_DST}"
rm -f "${tmp_unit}"

sudo systemctl daemon-reload
sudo systemctl enable mkm-compression-api-stub.service
echo "Installed ${UNIT_DST}. Start with: sudo systemctl start mkm-compression-api-stub"
echo "Health: curl -sS http://127.0.0.1:8010/health | head"
