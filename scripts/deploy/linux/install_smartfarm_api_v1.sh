#!/usr/bin/env bash
# Install smartfarm API dependencies + PM2 process (VPS).
#
# Usage (on VPS, repo already at REPO_ROOT):
#   sudo bash scripts/deploy/linux/install_smartfarm_api_v1.sh
#   sudo bash scripts/deploy/linux/install_smartfarm_api_v1.sh --apply-nginx /etc/nginx/sites-enabled/mkmlife.com
#
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
PM2_CONFIG="${REPO_ROOT}/scripts/deploy/linux/pm2_smartfarm_api.config.cjs"
VENV="${REPO_ROOT}/.venv-smartfarm"
APPLY_NGINX=0
NGINX_SITE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply-nginx)
      APPLY_NGINX=1
      NGINX_SITE="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "REPO_ROOT not found: $REPO_ROOT" >&2
  exit 2
fi

cd "$REPO_ROOT"

if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install -q --upgrade pip
pip install -q fastapi uvicorn pydantic paho-mqtt

mkdir -p "${REPO_ROOT}/reports"

if command -v pm2 >/dev/null 2>&1; then
  pm2 delete smartfarm-api 2>/dev/null || true
  pm2 start "$PM2_CONFIG"
  pm2 save || true
  echo "PM2 smartfarm-api started (127.0.0.1:8020)"
else
  echo "pm2 not found — start manually:" >&2
  echo "  source ${VENV}/bin/activate && uvicorn scripts.ai_smartfarm_api_stub:app --host 127.0.0.1 --port 8020" >&2
fi

if [[ "$APPLY_NGINX" -eq 1 ]]; then
  if [[ -z "$NGINX_SITE" ]]; then
    echo "--apply-nginx requires site file path" >&2
    exit 2
  fi
  bash "${REPO_ROOT}/scripts/deploy/linux/apply_farm_mkmlife_nginx_snippet.sh" -y "$NGINX_SITE"
fi

curl -sf "http://127.0.0.1:8020/health" | head -c 400 || echo "Health check pending (service warming up)"

echo "Done. Public API: farm-api.mkmlife.com (nginx) -> :8020"
