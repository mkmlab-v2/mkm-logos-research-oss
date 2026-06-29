#!/usr/bin/env bash
# Smoke test nvcr.io auth using NGC_API_KEY from .env (login only; no large pull).
set -euo pipefail
ENV_FILE="${MKM_WORKSPACE_ROOT:-/mnt/c/workspace}/.env"
API=$(grep -m1 '^NGC_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r"')
if [[ -z "$API" ]]; then
  echo "[ERROR] NGC_API_KEY missing in $ENV_FILE" >&2
  exit 1
fi
printf '%s' "$API" | docker login nvcr.io -u '$oauthtoken' --password-stdin
echo "[OK] nvcr.io docker login"
