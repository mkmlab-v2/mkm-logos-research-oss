#!/usr/bin/env bash
# HTTP-only no1kmedi.com apex portal (until certbot after DNS stable).
set -euo pipefail

AVAIL="/etc/nginx/sites-available/no1kmedi.com-portal"
ENABLED="/etc/nginx/sites-enabled/no1kmedi.com-portal"
UPSTREAM="${PORTAL_UPSTREAM:-http://127.0.0.1:3010}"
DO_APPLY=0
[[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]] && DO_APPLY=1

tee "$AVAIL" >/dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name no1kmedi.com www.no1kmedi.com;
    location / {
        proxy_pass ${UPSTREAM};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
ln -sf "$AVAIL" "$ENABLED"
echo "Installed HTTP-only portal $AVAIL -> $UPSTREAM"

if [[ "$DO_APPLY" -eq 1 ]] && [[ -z "${SKIP_NGINX_TEST:-}" ]]; then
  nginx -t
  systemctl reload nginx
fi
