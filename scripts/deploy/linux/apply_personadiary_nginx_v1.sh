#!/usr/bin/env bash
# Install personadiary.com nginx vhost (proxy → no1kmedi :3010).
# Run ON THE VPS with sudo.
#
# Usage:
#   sudo bash /opt/mkm-destiny-ai-41e38ec6/scripts/deploy/linux/apply_personadiary_nginx_v1.sh
#   sudo bash apply_personadiary_nginx_v1.sh -y
#
# Env:
#   PERSONADIARY_UPSTREAM  (default http://127.0.0.1:3010)
#   PERSONADIARY_SSL_DIR   (default /etc/letsencrypt/live/personadiary.com)
#
set -euo pipefailREPO_ROOT="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
EXAMPLE="$REPO_ROOT/scripts/deploy/linux/nginx-personadiary-com.conf.example"
SITE_AVAIL="/etc/nginx/sites-available/personadiary.com"
SITE_ENABLED="/etc/nginx/sites-enabled/personadiary.com"
PERSONADIARY_UPSTREAM="${PERSONADIARY_UPSTREAM:-http://127.0.0.1:3010}"
PERSONADIARY_SSL_DIR="${PERSONADIARY_SSL_DIR:-/etc/letsencrypt/live/personadiary.com}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
  shift
fi

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing example config: $EXAMPLE" >&2
  exit 2
fi

if [[ ! -d "$PERSONADIARY_SSL_DIR" ]]; then
  echo "WARN: SSL dir not found: $PERSONADIARY_SSL_DIR (run certbot first or edit $SITE_AVAIL)" >&2
fi

cp -a "$EXAMPLE" "$SITE_AVAIL"
sed -i "s|proxy_pass http://127.0.0.1:3010|proxy_pass ${PERSONADIARY_UPSTREAM}|g" "$SITE_AVAIL"
sed -i "s|/etc/letsencrypt/live/personadiary.com|${PERSONADIARY_SSL_DIR}|g" "$SITE_AVAIL"

ln -sf "$SITE_AVAIL" "$SITE_ENABLED"
echo "Installed: $SITE_ENABLED"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  echo "nginx reloaded."
else
  echo "Run: sudo nginx -t && sudo systemctl reload nginx"
fi
