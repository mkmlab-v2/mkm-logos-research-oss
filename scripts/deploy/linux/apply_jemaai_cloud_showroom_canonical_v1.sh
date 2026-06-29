#!/usr/bin/env bash
# Enable curated showroom on jemaai.cloud: UI snippet include + retire blanket public_showroom redirect.
# api.jemaai.cloud keeps full mirror; jemaai.cloud serves same /var/www/jemaai static via showroom_ui locations.
set -euo pipefail

JEMAAI_SITE="/etc/nginx/sites-enabled/jemaai.cloud"
API_SITE="/etc/nginx/sites-enabled/api.jemaai.cloud"
LEGACY_REDIRECT_SNIP="/etc/nginx/snippets/jemaai_showroom_legacy_redirect_v1.conf"
UI_SNIP="/etc/nginx/snippets/jemaai_showroom_ui.conf"
UI_INC="    include /etc/nginx/snippets/jemaai_showroom_ui.conf;"

backup() {
  local f="$1"
  [ -f "$f" ] || return 0
  cp -a "$f" "${f}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
}

strip_lens_audio_duplicate() {
  [ -f "$JEMAAI_SITE" ] || return 0
  if grep -q 'jemaai_lens_audio_static_v1.conf' "$JEMAAI_SITE"; then
    backup "$JEMAAI_SITE"
    sed -i '/jemaai_lens_audio_static_v1/d' "$JEMAAI_SITE"
    echo "stripped lens_audio include (showroom_ui superset)"
  fi
}

ensure_jemaai_ui() {
  [ -f "$JEMAAI_SITE" ] || { echo "missing $JEMAAI_SITE" >&2; exit 2; }
  if grep -q 'jemaai_showroom_ui.conf' "$JEMAAI_SITE"; then
    echo "jemaai.cloud showroom_ui already present"
    return 0
  fi
  backup "$JEMAAI_SITE"
  awk -v inc="$UI_INC" '
    /server_name/ && /jemaai\.cloud/ && !done { print; print inc; done=1; next }
    { print }
  ' "$JEMAAI_SITE" > "${JEMAAI_SITE}.new"
  mv "${JEMAAI_SITE}.new" "$JEMAAI_SITE"
  sed -i 's/jemaai_showroom_ui\.conf;;/jemaai_showroom_ui.conf;/' "$JEMAAI_SITE"
  echo "inserted showroom_ui on jemaai.cloud"
}

ensure_api_ui() {
  [ -f "$API_SITE" ] || return 0
  if grep -q 'jemaai_showroom_ui.conf' "$API_SITE"; then
    echo "api.jemaai.cloud showroom_ui already present"
    return 0
  fi
  backup "$API_SITE"
  awk -v inc="$UI_INC" '
    /server_name/ && /api\.jemaai\.cloud/ && !done { print; print inc; done=1; next }
    { print }
  ' "$API_SITE" > "${API_SITE}.new"
  mv "${API_SITE}.new" "$API_SITE"
  echo "inserted showroom_ui on api.jemaai.cloud"
}

strip_blanket_showroom_redirect() {
  [ -f "$LEGACY_REDIRECT_SNIP" ] || return 0
  if grep -q 'public_showroom_.\*\\.html' "$LEGACY_REDIRECT_SNIP"; then
    backup "$LEGACY_REDIRECT_SNIP"
    echo "WARN: legacy redirect still blocks public_showroom_*.html — redeploy snippet from repo" >&2
  else
    echo "legacy redirect OK (no blanket public_showroom block)"
  fi
}

[ -f "$UI_SNIP" ] || { echo "missing $UI_SNIP — scp jemaai_showroom_ui.conf first" >&2; exit 2; }

strip_lens_audio_duplicate
ensure_jemaai_ui
ensure_api_ui
strip_blanket_showroom_redirect

echo "=== jemaai.cloud includes ==="
grep -n 'include ' "$JEMAAI_SITE" || true

nginx -t
systemctl reload nginx
echo "nginx reloaded OK — jemaai.cloud showroom canonical enabled"
