#!/usr/bin/env bash
set -euo pipefail

# Canonical live runner: load repo-root .env, then start trader entrypoint.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../../" && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
ENTRYPOINT="${REPO_ROOT}/projects/bitcoin-trading/start_live_trading.py"

cd "${REPO_ROOT}/projects/bitcoin-trading"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

exec python3 "${ENTRYPOINT}" "$@"
