#!/usr/bin/env bash
# Install farm.mkmlife.com / farm-api.mkmlife.com nginx snippets (idempotent).
# Run ON THE TARGET VPS with sudo.
#
# Usage:
#   sudo bash apply_farm_mkmlife_nginx_snippet.sh
#   sudo bash apply_farm_mkmlife_nginx_snippet.sh /etc/nginx/sites-enabled/mkmlife.com
#   sudo bash apply_farm_mkmlife_nginx_snippet.sh -y /etc/nginx/sites-enabled/mkmlife.com
#
# Env:
#   FARM_UI_UPSTREAM   (default http://127.0.0.1:5173)
#   FARM_API_UPSTREAM  (default http://127.0.0.1:8020)
#
set -euo pipefail

SNIP_DIR="/etc/nginx/snippets"
FARM_UI_SNIP="$SNIP_DIR/mkm_farm_ui.conf"
FARM_API_SNIP="$SNIP_DIR/mkm_farm_api.conf"
UI_INCLUDE_LINE='    include /etc/nginx/snippets/mkm_farm_ui.conf;'
API_INCLUDE_LINE='    include /etc/nginx/snippets/mkm_farm_api.conf;'

FARM_UI_UPSTREAM="${FARM_UI_UPSTREAM:-http://127.0.0.1:5173}"
FARM_API_UPSTREAM="${FARM_API_UPSTREAM:-http://127.0.0.1:8020}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
  shift
fi
SITE="${1:-}"

mkdir -p "$SNIP_DIR"

tee "$FARM_UI_SNIP" >/dev/null <<EOF
# mkm_farm_ui.conf
location / {
    proxy_pass ${FARM_UI_UPSTREAM};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
EOF

tee "$FARM_API_SNIP" >/dev/null <<EOF
# mkm_farm_api.conf
location / {
    proxy_pass ${FARM_API_UPSTREAM};
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
}
EOF

echo "Wrote snippets:"
echo " - $FARM_UI_SNIP"
echo " - $FARM_API_SNIP"

if [[ -z "$SITE" ]]; then
  cat <<EOT
No site file passed.

For server_name farm.mkmlife.com:
${UI_INCLUDE_LINE}

For server_name farm-api.mkmlife.com:
${API_INCLUDE_LINE}
EOT
  exit 0
fi

if [[ ! -f "$SITE" ]]; then
  echo "Site file not found: $SITE" >&2
  exit 2
fi

BACKUP="${SITE}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp -a "$SITE" "$BACKUP"
echo "Backup: $BACKUP"

if ! grep -qF "mkm_farm_ui.conf" "$SITE"; then
  awk -v inc="$UI_INCLUDE_LINE" '
    BEGIN { done=0 }
    {
      print $0
      if (!done && $0 ~ /server_name/ && $0 ~ /farm\.mkmlife\.com/) {
        print inc
        done=1
      }
    }
  ' "$SITE" > "${SITE}.new1"
  mv "${SITE}.new1" "$SITE"
  echo "Inserted farm UI include."
else
  echo "farm UI include already present."
fi

if ! grep -qF "mkm_farm_api.conf" "$SITE"; then
  awk -v inc="$API_INCLUDE_LINE" '
    BEGIN { done=0 }
    {
      print $0
      if (!done && $0 ~ /server_name/ && $0 ~ /farm-api\.mkmlife\.com/) {
        print inc
        done=1
      }
    }
  ' "$SITE" > "${SITE}.new2"
  mv "${SITE}.new2" "$SITE"
  echo "Inserted farm API include."
else
  echo "farm API include already present."
fi

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  echo "nginx reloaded."
else
  echo "Run: sudo nginx -t && sudo systemctl reload nginx"
fi
