#!/usr/bin/env bash
# no1kmedi.com apex portal → Next :3010 (한의사 /clinician). api.* is separate.
set -euo pipefail

REPO_ROOT="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
EXAMPLE="$REPO_ROOT/scripts/deploy/linux/nginx-no1kmedi-com-portal.conf.example"
SITE_AVAIL="/etc/nginx/sites-available/no1kmedi.com-portal"
SITE_ENABLED="/etc/nginx/sites-enabled/no1kmedi.com-portal"
PORTAL_UPSTREAM="${PORTAL_UPSTREAM:-http://127.0.0.1:3010}"
PORTAL_SSL_DIR="${PORTAL_SSL_DIR:-/etc/letsencrypt/live/no1kmedi.com}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
fi

cp -a "$EXAMPLE" "$SITE_AVAIL"
sed -i "s|proxy_pass http://127.0.0.1:3010|proxy_pass ${PORTAL_UPSTREAM}|g" "$SITE_AVAIL"
sed -i "s|/etc/letsencrypt/live/no1kmedi.com|${PORTAL_SSL_DIR}|g" "$SITE_AVAIL"
ln -sf "$SITE_AVAIL" "$SITE_ENABLED"
echo "Installed no1kmedi.com portal (ensure no conflict with legacy apex vhost)"

if [[ ! -f "${PORTAL_SSL_DIR}/fullchain.pem" ]]; then
  echo "Missing ${PORTAL_SSL_DIR}/fullchain.pem — run certbot for no1kmedi.com or use apply_no1kmedi_com_portal_http_only_v1.sh" >&2
  exit 3
fi

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
fi
