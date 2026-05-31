#!/usr/bin/env bash
# mkmlab.space HTTP 301 only (SSL optional when cert exists).
set -euo pipefail

AVAIL="/etc/nginx/sites-available/mkmlab.space"
ENABLED="/etc/nginx/sites-enabled/mkmlab.space"
TARGET="${MKMLAB_RETIRE_TARGET:-https://research.no1kmedi.com}"
DO_APPLY=0
[[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]] && DO_APPLY=1

tee "$AVAIL" >/dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name mkmlab.space www.mkmlab.space;
    return 301 ${TARGET}\$request_uri;
}
EOF

if [[ -f /etc/letsencrypt/live/mkmlab.space/fullchain.pem ]]; then
  tee -a "$AVAIL" >/dev/null <<EOF

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
fi

ln -sf "$AVAIL" "$ENABLED"
echo "mkmlab.space 301 -> $TARGET"

if [[ "$DO_APPLY" -eq 1 ]] && [[ -z "${SKIP_NGINX_TEST:-}" ]]; then
  nginx -t
  systemctl reload nginx
fi
