#!/usr/bin/env bash
# Install farm.jema-ai.com nginx vhost (proxy → no1kmedi :3010).
# Run ON THE VPS with sudo.
#
# Usage:
#   sudo bash /opt/mkm-destiny-ai-41e38ec6/scripts/deploy/linux/apply_farm_jema_ai_nginx_v1.sh
#   sudo bash apply_farm_jema_ai_nginx_v1.sh -y
#
# Env:
#   FARM_JEMA_UPSTREAM  (default http://127.0.0.1:3010)
#   FARM_JEMA_SSL_DIR   (default /etc/letsencrypt/live/farm.jema-ai.com)
#
set -euo pipefail

REPO_ROOT="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
EXAMPLE="$REPO_ROOT/scripts/deploy/linux/nginx-farm-jema-ai-com.conf.example"
SITE_AVAIL="/etc/nginx/sites-available/farm.jema-ai.com"
SITE_ENABLED="/etc/nginx/sites-enabled/farm.jema-ai.com"
FARM_JEMA_UPSTREAM="${FARM_JEMA_UPSTREAM:-http://127.0.0.1:3010}"
FARM_JEMA_SSL_DIR="${FARM_JEMA_SSL_DIR:-/etc/letsencrypt/live/farm.jema-ai.com}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
  shift
fi

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing example config: $EXAMPLE" >&2
  exit 2
fi

if [[ ! -d "$FARM_JEMA_SSL_DIR" ]]; then
  echo "WARN: SSL dir not found: $FARM_JEMA_SSL_DIR (edit $SITE_AVAIL after certbot)" >&2
fi

cp -a "$EXAMPLE" "$SITE_AVAIL"
sed -i "s|proxy_pass http://127.0.0.1:3010|proxy_pass ${FARM_JEMA_UPSTREAM}|g" "$SITE_AVAIL"
sed -i "s|/etc/letsencrypt/live/jema-ai.com|${FARM_JEMA_SSL_DIR}|g" "$SITE_AVAIL"

ln -sf "$SITE_AVAIL" "$SITE_ENABLED"
echo "Installed: $SITE_ENABLED"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  echo "nginx reloaded."
else
  echo "Run: sudo nginx -t && sudo systemctl reload nginx"
fi
