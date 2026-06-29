#!/usr/bin/env bash
# Fix jemaai.cloud nginx: drop full showroom_ui snippet (duplicates jemaai_public_showroom.conf),
# keep lens-audio-only snippet for WAV MIME. api.jemaai.cloud keeps full UI snippet.
set -euo pipefail

JEMAAI_SITE="/etc/nginx/sites-enabled/jemaai.cloud"
API_SITE="/etc/nginx/sites-enabled/api.jemaai.cloud"
PUB_SNIP="/etc/nginx/snippets/jemaai_public_showroom.conf"
UI_SNIP="/etc/nginx/snippets/jemaai_showroom_ui.conf"
AUDIO_SNIP="/etc/nginx/snippets/jemaai_lens_audio_static_v1.conf"
UI_INC="include /etc/nginx/snippets/jemaai_showroom_ui.conf"
AUDIO_INC="include /etc/nginx/snippets/jemaai_lens_audio_static_v1.conf"

backup() {
  local f="$1"
  [ -f "$f" ] || return 0
  cp -a "$f" "${f}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
}

strip_ui_includes() {
  local f="$1"
  [ -f "$f" ] || return 0
  if grep -q 'jemaai_showroom_ui' "$f"; then
    backup "$f"
    sed -i '/jemaai_showroom_ui/d' "$f"
    echo "stripped showroom_ui from $f"
  fi
}

ensure_api_ui() {
  [ -f "$API_SITE" ] || { echo "skip missing $API_SITE"; return 0; }
  if grep -q 'jemaai_showroom_ui.conf' "$API_SITE"; then
    echo "api UI snippet already present"
    return 0
  fi
  backup "$API_SITE"
  awk -v inc="    $UI_INC;" '
    /server_name/ && /api\.jemaai\.cloud/ && !done { print; print inc; done=1; next }
    { print }
  ' "$API_SITE" > "${API_SITE}.new"
  mv "${API_SITE}.new" "$API_SITE"
  echo "inserted UI snippet on api.jemaai.cloud"
}

ensure_public_audio() {
  [ -f "$JEMAAI_SITE" ] || { echo "missing $JEMAAI_SITE" >&2; exit 2; }
  if grep -q 'jemaai_lens_audio_static_v1.conf' "$JEMAAI_SITE"; then
    echo "jemaai.cloud lens audio snippet already present"
    return 0
  fi
  backup "$JEMAAI_SITE"
  awk -v inc="    $AUDIO_INC;" '
    /server_name/ && /jemaai\.cloud/ && !done { print; print inc; done=1; next }
    { print }
  ' "$JEMAAI_SITE" > "${JEMAAI_SITE}.new"
  mv "${JEMAAI_SITE}.new" "$JEMAAI_SITE"
  echo "inserted lens audio snippet on jemaai.cloud"
}

[ -f "$AUDIO_SNIP" ] || { echo "missing $AUDIO_SNIP" >&2; exit 2; }

strip_ui_includes "$JEMAAI_SITE"
strip_ui_includes "$PUB_SNIP"
ensure_api_ui
ensure_public_audio

echo "=== jemaai.cloud includes (after) ==="
grep -n 'include ' "$JEMAAI_SITE" || true

nginx -t
systemctl reload nginx
echo "nginx reloaded OK"
