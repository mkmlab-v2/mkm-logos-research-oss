#!/usr/bin/env bash
# mkmlab.space → 301 https://research.no1kmedi.com (before registrar expiry).
set -euo pipefail

SITE_NAME="mkmlab.space"
AVAIL="/etc/nginx/sites-available/${SITE_NAME}"
ENABLED="/etc/nginx/sites-enabled/${SITE_NAME}"
TARGET="${MKMLAB_RETIRE_TARGET:-https://research.no1kmedi.com}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
fi

tee "$AVAIL" >/dev/null <<EOF
# mkmlab.space retire 301 (apply_mkmlab_space_retire_301_v1.sh)
server {
    listen 80;
    listen [::]:80;
    server_name mkmlab.space www.mkmlab.space;
    return 301 ${TARGET}\$request_uri;
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name mkmlab.space www.mkmlab.space;
    ssl_certificate     /etc/letsencrypt/live/mkmlab.space/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mkmlab.space/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    return 301 ${TARGET}\$request_uri;
}
EOF

ln -sf "$AVAIL" "$ENABLED"
echo "mkmlab.space will 301 -> $TARGET"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx
fi
