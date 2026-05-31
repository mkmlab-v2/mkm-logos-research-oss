#!/usr/bin/env bash
# clinic.no1kmedi.com → Next :3010
set -euo pipefail

REPO_ROOT="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
EXAMPLE="$REPO_ROOT/scripts/deploy/linux/nginx-clinic-no1kmedi-com.conf.example"
SITE_AVAIL="/etc/nginx/sites-available/clinic.no1kmedi.com"
SITE_ENABLED="/etc/nginx/sites-enabled/clinic.no1kmedi.com"
CLINIC_UPSTREAM="${CLINIC_UPSTREAM:-http://127.0.0.1:3010}"
CLINIC_SSL_DIR="${CLINIC_SSL_DIR:-/etc/letsencrypt/live/clinic.no1kmedi.com}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
fi

cp -a "$EXAMPLE" "$SITE_AVAIL"
sed -i "s|proxy_pass http://127.0.0.1:3010|proxy_pass ${CLINIC_UPSTREAM}|g" "$SITE_AVAIL"
sed -i "s|/etc/letsencrypt/live/clinic.no1kmedi.com|${CLINIC_SSL_DIR}|g" "$SITE_AVAIL"
ln -sf "$SITE_AVAIL" "$SITE_ENABLED"
echo "Installed clinic.no1kmedi.com"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
fi
