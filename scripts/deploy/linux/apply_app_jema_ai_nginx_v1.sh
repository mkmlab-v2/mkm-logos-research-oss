#!/usr/bin/env bash
# Install app.jema-ai.com nginx vhost (proxy → no1kmedi :3010).
# Removes legacy /smartfarm → /consumer rewrite; Next middleware 308 → farm.jema-ai.com.
#
# Usage:
#   sudo bash /opt/mkm-destiny-ai-41e38ec6/scripts/deploy/linux/apply_app_jema_ai_nginx_v1.sh -y
#
# Env:
#   APP_JEMA_UPSTREAM  (default http://127.0.0.1:3010)
#   APP_JEMA_SSL_DIR   (default /etc/letsencrypt/live/app.jema-ai.com)
#
set -euo pipefail

REPO_ROOT="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
EXAMPLE="$REPO_ROOT/scripts/deploy/linux/nginx-app-jema-ai-com.conf.example"
SITE_AVAIL="/etc/nginx/sites-available/app.jema-ai.com"
SITE_ENABLED="/etc/nginx/sites-enabled/app.jema-ai.com"
APP_JEMA_UPSTREAM="${APP_JEMA_UPSTREAM:-http://127.0.0.1:3010}"
APP_JEMA_SSL_DIR="${APP_JEMA_SSL_DIR:-/etc/letsencrypt/live/app.jema-ai.com}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
  shift
fi

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing example config: $EXAMPLE" >&2
  exit 2
fi

if [[ -f "$SITE_AVAIL" ]]; then
  cp -a "$SITE_AVAIL" "${SITE_AVAIL}.bak.$(date +%Y%m%d_%H%M%S)"
fi

cp -a "$EXAMPLE" "$SITE_AVAIL"
sed -i "s|proxy_pass http://127.0.0.1:3010|proxy_pass ${APP_JEMA_UPSTREAM}|g" "$SITE_AVAIL"
sed -i "s|/etc/letsencrypt/live/app.jema-ai.com|${APP_JEMA_SSL_DIR}|g" "$SITE_AVAIL"

ln -sf "$SITE_AVAIL" "$SITE_ENABLED"
echo "Installed: $SITE_ENABLED"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  echo "nginx reloaded."
else
  echo "Run: sudo nginx -t && sudo systemctl reload nginx"
fi
