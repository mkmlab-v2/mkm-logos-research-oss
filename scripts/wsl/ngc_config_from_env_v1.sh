#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/mnt/c/workspace/.env"
NGC_BIN="${HOME}/.local/ngc-cli/ngc-cli/ngc"
export PATH="${HOME}/.local/bin:${PATH}"

API_KEY=""
ORG="0973911188260618"

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line//$'\r'/}"
  line="${line%%#*}"
  if [[ "$line" =~ ^[[:space:]]*NGC_API_KEY[[:space:]]*=[[:space:]]*(.+)[[:space:]]*$ ]]; then
    API_KEY="${BASH_REMATCH[1]}"
    API_KEY="${API_KEY%\"}"; API_KEY="${API_KEY#\"}"
  elif [[ "$line" =~ ^[[:space:]]*NGC_ORG[[:space:]]*=[[:space:]]*(.+)[[:space:]]*$ ]]; then
    ORG="${BASH_REMATCH[1]}"
    ORG="${ORG//$'\r'/}"
    ORG="${ORG%\"}"; ORG="${ORG#\"}"
  fi
done < "$ENV_FILE"

if [[ -z "$API_KEY" ]]; then
  echo "[ERROR] NGC_API_KEY missing in .env" >&2
  exit 1
fi

"$NGC_BIN" config clear >/dev/null 2>&1 || true
rm -rf "${HOME}/.ngc"

# Non-interactive: api-key, format, org (3 prompts only)
printf '%s\nascii\n%s\n' "$API_KEY" "$ORG" | "$NGC_BIN" config set --auth-option api-key

echo "[OK] ngc config saved (org=$ORG)"
"$NGC_BIN" config current
"$NGC_BIN" user who --format_type json
