#!/usr/bin/env bash
# api.jemaai.cloud: push legacy-aware showroom_ui snippet + reload nginx.
set -euo pipefail

UI_SNIP="/etc/nginx/snippets/jemaai_showroom_ui.conf"
UI_SRC="${1:-/tmp/jemaai_showroom_ui.conf}"

if [[ ! -f "${UI_SRC}" ]]; then
  echo "missing UI snippet source: ${UI_SRC}" >&2
  exit 1
fi

sudo install -m 0644 "${UI_SRC}" "${UI_SNIP}"
echo "installed ${UI_SNIP}"

sudo nginx -t
sudo systemctl reload nginx
echo "api.jemaai.cloud showroom_ui reloaded"
