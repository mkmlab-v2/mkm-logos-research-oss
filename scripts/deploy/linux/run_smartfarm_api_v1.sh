#!/usr/bin/env bash
# Run smartfarm API (uvicorn) — used by PM2 on VPS.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
VENV="${REPO_ROOT}/.venv-smartfarm"

cd "$REPO_ROOT"
if [[ -f "${VENV}/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
fi

exec uvicorn scripts.ai_smartfarm_api_stub:app --host 127.0.0.1 --port 8020
