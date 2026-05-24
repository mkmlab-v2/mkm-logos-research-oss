#!/usr/bin/env bash
# Install mkm-logos-trace-api-stub.service on Linux (VPS). Requires sudo.
#
# Usage:
#   export WORKSPACE_ROOT=/opt/mkm-destiny-ai-41e38ec6
#   sudo -E bash scripts/deploy/linux/install_logos_trace_api_stub_systemd.sh
#
# After static sync: curl -sS http://127.0.0.1:8021/health
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_SRC="${SCRIPT_DIR}/mkm-logos-trace-api-stub.service"
UNIT_DST="/etc/systemd/system/mkm-logos-trace-api-stub.service"
ENV_DIR="/etc/mkm"
ENV_DST="${ENV_DIR}/logos-trace-api.env"
NGINX_SNIP="${SCRIPT_DIR}/nginx-logos-trace-api.conf.example"
NGINX_DST="/etc/nginx/snippets/mkm_logos_trace_api.conf"

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
  sudo cp "${SCRIPT_DIR}/logos-trace-api.env.example" "${ENV_DST}"
fi

tmp_unit="$(mktemp)"
sed -e "s|WorkingDirectory=.*|WorkingDirectory=${WORKSPACE_ROOT}|" \
    -e "s|Environment=PYTHONPATH=.*|Environment=PYTHONPATH=${WORKSPACE_ROOT}|" \
    "${SERVICE_SRC}" >"${tmp_unit}"
sudo cp "${tmp_unit}" "${UNIT_DST}"
rm -f "${tmp_unit}"

if [[ -f "${NGINX_SNIP}" ]]; then
  sudo cp "${NGINX_SNIP}" "${NGINX_DST}"
  echo "Installed nginx snippet ${NGINX_DST}"
  echo "Ensure api.jemaai.cloud server { } includes: include /etc/nginx/snippets/mkm_logos_trace_api.conf;"
fi

sudo systemctl daemon-reload
sudo systemctl enable mkm-logos-trace-api-stub.service
sudo systemctl restart mkm-logos-trace-api-stub.service || sudo systemctl start mkm-logos-trace-api-stub.service

sleep 1
if curl -fsS "http://127.0.0.1:8021/health" >/dev/null; then
  echo "OK: http://127.0.0.1:8021/health"
  curl -sS "http://127.0.0.1:8021/health" | head -c 400
  echo
else
  echo "WARN: health check failed — journalctl -u mkm-logos-trace-api-stub -n 40" >&2
  exit 1
fi
