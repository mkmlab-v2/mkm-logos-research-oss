#!/usr/bin/env bash
# Deploy payapp-api on Hostinger VPS (compute only — no hPanel public_html).
# SSOT: docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm required" >&2
  exit 1
fi
if ! command -v pm2 >/dev/null 2>&1; then
  echo "pm2 required" >&2
  exit 1
fi

npm ci --omit=dev 2>/dev/null || npm install --omit=dev

if pm2 describe no1kmedi-payapp-api >/dev/null 2>&1; then
  pm2 restart ecosystem.config.cjs --only no1kmedi-payapp-api --update-env
else
  pm2 start ecosystem.config.cjs --only no1kmedi-payapp-api
fi
pm2 save

echo "--- localhost health (origin, bypass Cloudflare) ---"
curl -sS -m 5 "http://127.0.0.1:3847/health" || true
echo
echo "Done. Public URL needs nginx origin -> :3847 and CF DNS to this VPS."
