#!/usr/bin/env bash
# Install jemaai showroom static locations under /etc/nginx/snippets/jemaai_showroom_ui.conf
# Run ON THE VPS with sudo (or via sync_showroom_to_vps.ps1 -ApplyRecommendedNginx).
#
# Usage:
#   sudo bash apply_jemaai_showroom_nginx_snippet.sh
#   sudo bash apply_jemaai_showroom_nginx_snippet.sh -y /etc/nginx/sites-enabled/api.jemaai.cloud
#
set -euo pipefail

SNIP_DIR="/etc/nginx/snippets"
SNIP_FILE="$SNIP_DIR/jemaai_showroom_ui.conf"
MARK="# jemaai_showroom_ui"
INCLUDE_LINE='    include /etc/nginx/snippets/jemaai_showroom_ui.conf;'

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
  shift
fi
SITE="${1:-}"

SRC="${MKM_SHOWROOM_SNIP_SRC:-}"
if [[ -z "$SRC" ]]; then
  for c in \
    "/opt/mkm-lab-workspace-v2/projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/nginx_snippets/jemaai_showroom_ui.conf" \
    "/var/www/jemaai/nginx_snippets/jemaai_showroom_ui.conf"; do
    if [[ -f "$c" ]]; then SRC="$c"; break; fi
  done
fi

if [[ -n "$SRC" ]] && [[ -f "$SRC" ]]; then
  mkdir -p "$SNIP_DIR"
  cp -a "$SRC" "$SNIP_FILE"
  echo "Copied $SRC -> $SNIP_FILE"
elif [[ ! -f "$SNIP_FILE" ]]; then
  echo "Missing snippet: set MKM_SHOWROOM_SNIP_SRC or scp jemaai_showroom_ui.conf to $SNIP_FILE" >&2
  exit 2
else
  echo "Using existing $SNIP_FILE"
fi

if [[ -z "$SITE" ]]; then
  echo "Snippet ready. Ensure api.jemaai.cloud server { } includes:"
  echo "$INCLUDE_LINE"
  exit 0
fi

if [[ ! -f "$SITE" ]]; then
  echo "Site file not found: $SITE" >&2
  exit 2
fi

if grep -qF "jemaai_showroom_ui.conf" "$SITE"; then
  echo "Include already present in $SITE"
else
  BACKUP="${SITE}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "$SITE" "$BACKUP"
  echo "Backup: $BACKUP"
  if grep -qE 'server_name\s+.*api\.jemaai\.cloud' "$SITE"; then
    awk -v inc="$INCLUDE_LINE" '
      BEGIN { done=0 }
      {
        print $0
        if (!done && $0 ~ /server_name/ && $0 ~ /api\.jemaai\.cloud/) {
          print inc
          done=1
        }
      }
    ' "$SITE" | tee "${SITE}.new" >/dev/null
    mv "${SITE}.new" "$SITE"
    echo "Inserted include after server_name (api.jemaai.cloud) in $SITE"
  else
    echo "Add manually inside server { }:" >&2
    echo "$INCLUDE_LINE" >&2
    exit 3
  fi
fi

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx
  echo "nginx reloaded"
fi
