#!/usr/bin/env bash
# PM2 entry for no1kmedi-com — keep in tarball so Destiny deploy does not wipe the start path.
# Secrets: sourced from .env.local on VPS (never commit). research_only · SEND HOLD
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f .env.local ]]; then
  # shellcheck disable=SC1091
  set -a
  # Export only ACODEAI_CREEM_* lines (avoid sourcing unrelated keys with spaces)
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      ACODEAI_CREEM_*=*)
        key="${line%%=*}"
        val="${line#*=}"
        export "$key=$val"
        ;;
    esac
  done < .env.local
  set +a
fi
export NODE_ENV=production
exec npm start
