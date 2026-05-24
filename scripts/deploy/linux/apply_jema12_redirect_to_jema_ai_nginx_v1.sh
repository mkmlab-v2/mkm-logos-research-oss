#!/usr/bin/env bash
# Replace jema12.com nginx vhost with 301 → https://jema-ai.com (keeps LE certs).
set -euo pipefail

SITE_AVAILABLE="/etc/nginx/sites-available/jema12.com"
SITE_ENABLED="/etc/nginx/sites-enabled/jema12.com"
SNIP_SRC="$(cd "$(dirname "$0")" && pwd)/nginx_jema12_redirect_to_jema_ai_v1.conf"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ ! -f "$SNIP_SRC" ]]; then
  echo "missing $SNIP_SRC" >&2
  exit 1
fi

if [[ -f "$SITE_AVAILABLE" ]]; then
  cp -a "$SITE_AVAILABLE" "${SITE_AVAILABLE}.bak.${STAMP}"
  echo "backup: ${SITE_AVAILABLE}.bak.${STAMP}"
fi

cp "$SNIP_SRC" "$SITE_AVAILABLE"
ln -sf "$SITE_AVAILABLE" "$SITE_ENABLED"

nginx -t
systemctl reload nginx
echo "OK: jema12.com → https://jema-ai.com (301)"
