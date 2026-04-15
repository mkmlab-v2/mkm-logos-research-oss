#!/usr/bin/env bash
set -euo pipefail

# Apply small live-trading defaults into repo-root .env safely.
# Usage:
#   bash projects/bitcoin-trading/ops/v2/ssh/apply_small_live_env.sh /opt/mkm-destiny-ai-41e38ec6 150

REPO_ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../" && pwd)}"
INITIAL_CAPITAL="${2:-150}"
ENV_PATH="${REPO_ROOT}/.env"

mkdir -p "$(dirname "${ENV_PATH}")"
touch "${ENV_PATH}"
chmod 600 "${ENV_PATH}" 2>/dev/null || true

upsert_kv() {
  local key="$1"
  local val="$2"
  if rg -n "^${key}=" "${ENV_PATH}" >/dev/null 2>&1; then
    sed -i "s|^${key}=.*|${key}=${val}|g" "${ENV_PATH}"
  else
    printf "%s=%s\n" "${key}" "${val}" >> "${ENV_PATH}"
  fi
}

upsert_kv "TESTNET" "0"
upsert_kv "ENABLE_TRADING" "1"
upsert_kv "DISABLE_PROPHECY_STACK" "0"
upsert_kv "PROPHECY_FUSION_ALLOW_MAINNET" "1"
upsert_kv "INITIAL_CAPITAL" "${INITIAL_CAPITAL}"
upsert_kv "LEVERAGE" "2"
upsert_kv "RISK_PROFILE_MAX_AGE_MINUTES" "60"

echo "Applied small-live env profile to: ${ENV_PATH}"
echo "INITIAL_CAPITAL=${INITIAL_CAPITAL}, LEVERAGE=2, TESTNET=0, ENABLE_TRADING=1"
