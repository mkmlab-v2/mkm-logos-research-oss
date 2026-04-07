#!/usr/bin/env bash
# Install MKM12 jema12 routes as an nginx include + optional one-line hook.
# Run ON THE PRODUCTION SERVER with sudo.
#
# 1) Writes /etc/nginx/snippets/mkm12_jema12_public_routes.conf (idempotent content).
# 2) If SITE file is given, ensures a single include line exists inside the jema12 server block
#    (best-effort: after first "server_name" line containing jema12).
#
# Usage:
#   sudo bash apply_jema12_nginx_snippet.sh
#   sudo bash apply_jema12_nginx_snippet.sh /etc/nginx/sites-enabled/jema12.com
#   sudo bash apply_jema12_nginx_snippet.sh -y /etc/nginx/sites-enabled/jema12.com   # nginx -t && reload
#
# Env: BROADCAST_TARGET (default https://api.jemaai.cloud/public_showroom_poll.html)
#
set -euo pipefail

SNIP_DIR="/etc/nginx/snippets"
SNIP_FILE="$SNIP_DIR/mkm12_jema12_public_routes.conf"
INCLUDE_LINE='    include /etc/nginx/snippets/mkm12_jema12_public_routes.conf;'
MARK="# mkm12_jema12_public_routes"
BROADCAST_TARGET="${BROADCAST_TARGET:-https://api.jemaai.cloud/public_showroom_poll.html}"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
  shift
fi
SITE="${1:-}"

mkdir -p "$SNIP_DIR"
tee "$SNIP_FILE" >/dev/null <<EOF
$MARK
location = /studio {
    return 301 /studio/;
}
location = /broadcast {
    return 302 ${BROADCAST_TARGET};
}
EOF
echo "Wrote $SNIP_FILE"

if [[ -z "$SITE" ]]; then
  echo "No site file passed. Add inside jema12.com server { }:"
  echo "$INCLUDE_LINE"
  exit 0
fi

if [[ ! -f "$SITE" ]]; then
  echo "Site file not found: $SITE" >&2
  exit 2
fi

if grep -qF "mkm12_jema12_public_routes.conf" "$SITE"; then
  echo "Include already present in $SITE"
else
  BACKUP="${SITE}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "$SITE" "$BACKUP"
  echo "Backup: $BACKUP"
  # Insert include after first line that looks like server_name ... jema12
  if grep -qE 'server_name\s+.*jema12' "$SITE"; then
    awk -v inc="$INCLUDE_LINE" '
      BEGIN { done=0 }
      {
        print $0
        if (!done && $0 ~ /server_name/ && $0 ~ /jema12/) {
          print inc
          done=1
        }
      }
    ' "$SITE" | tee "${SITE}.new" >/dev/null
    mv "${SITE}.new" "$SITE"
    echo "Inserted include after server_name (jema12) in $SITE"
  else
    echo "Could not find server_name line with jema12 — add manually inside server { }:" >&2
    echo "$INCLUDE_LINE" >&2
    exit 3
  fi
fi

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  echo "nginx reloaded."
else
  echo "Run: sudo nginx -t && sudo systemctl reload nginx"
fi
