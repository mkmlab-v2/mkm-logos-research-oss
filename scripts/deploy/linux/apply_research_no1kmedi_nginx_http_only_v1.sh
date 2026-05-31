#!/usr/bin/env bash
# HTTP-only research.no1kmedi.com (use until certbot succeeds after DNS propagates).
set -euo pipefail

AVAIL="/etc/nginx/sites-available/research.no1kmedi.com"
ENABLED="/etc/nginx/sites-enabled/research.no1kmedi.com"
ROOT="/var/www/mkmlab"
DO_APPLY=0
[[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]] && DO_APPLY=1

mkdir -p "$ROOT"
tee "$AVAIL" >/dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name research.no1kmedi.com;
    root $ROOT;
    index index.html en.html;
    location / { try_files \$uri \$uri/ =404; }
}
EOF
ln -sf "$AVAIL" "$ENABLED"
echo "Installed HTTP-only $AVAIL"

if [[ "$DO_APPLY" -eq 1 ]] && [[ -z "${SKIP_NGINX_TEST:-}" ]]; then
  nginx -t
  systemctl reload nginx
fi
