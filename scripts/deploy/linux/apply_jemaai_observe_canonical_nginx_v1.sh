#!/usr/bin/env bash
# jemaai.cloud: index.html -> public_observe_v1; 301 retired pixel showroom URLs.
set -euo pipefail

SITE="/etc/nginx/sites-enabled/jemaai.cloud"
PUBLIC_SNIP="/etc/nginx/snippets/jemaai_public_showroom.conf"
REDIRECT_SNIP="/etc/nginx/snippets/jemaai_showroom_legacy_redirect_v1.conf"
REDIRECT_SRC="${1:-/tmp/jemaai_showroom_legacy_redirect_v1.conf}"
NOINDEX_SNIP="/etc/nginx/snippets/jemaai_showroom_legacy_noindex_v1.conf"
NOINDEX_SRC="${2:-/tmp/jemaai_showroom_legacy_noindex_v1.conf}"

if [[ ! -f "${SITE}" ]]; then
  echo "missing site: ${SITE}" >&2
  exit 1
fi

sudo cp -a "${SITE}" "${SITE}.bak_observe_v1_$(date +%Y%m%d%H%M%S)"

if [[ ! -f "${REDIRECT_SRC}" ]]; then
  echo "missing redirect snippet source: ${REDIRECT_SRC}" >&2
  exit 1
fi
sudo install -m 0644 "${REDIRECT_SRC}" "${REDIRECT_SNIP}"
echo "installed ${REDIRECT_SNIP}"

if ! grep -q 'jemaai_showroom_legacy_redirect_v1.conf' "${SITE}"; then
  sudo sed -i '/include \/etc\/nginx\/snippets\/jemaai_public_showroom.conf;/a\    include /etc/nginx/snippets/jemaai_showroom_legacy_redirect_v1.conf;' "${SITE}"
  echo "inserted legacy redirect include"
fi

if [[ -f "${NOINDEX_SRC}" ]]; then
  sudo install -m 0644 "${NOINDEX_SRC}" "${NOINDEX_SNIP}"
  echo "installed ${NOINDEX_SNIP}"
  if ! grep -q 'jemaai_showroom_legacy_noindex_v1.conf' "${SITE}"; then
    sudo sed -i '/include \/etc\/nginx\/snippets\/jemaai_showroom_legacy_redirect_v1.conf;/a\    include /etc/nginx/snippets/jemaai_showroom_legacy_noindex_v1.conf;' "${SITE}"
    echo "inserted legacy noindex include"
  fi
fi

sudo sed -i 's/^[[:space:]]*index public_showroom_poll\.html;/    index index.html;/' "${SITE}"
sudo sed -i 's|try_files \$uri /public_showroom_poll\.html;|try_files $uri $uri/ /index.html;|' "${SITE}"

if [[ -f "${PUBLIC_SNIP}" ]]; then
  sudo sed -i 's|alias /var/www/jemaai/public_showroom_poll\.html;|return 301 /public_observe_v1.html;|' "${PUBLIC_SNIP}"
  sudo sed -i '/location = \/public_showroom_poll\.html/,/}/ s/alias /return 301 \/public_observe_v1.html; # was alias /' "${PUBLIC_SNIP}" 2>/dev/null || true
  if grep -q 'alias /var/www/jemaai/public_showroom_poll.html' "${PUBLIC_SNIP}"; then
    sudo tee "${PUBLIC_SNIP}" >/dev/null <<'EOF'
# public showroom API -> gateway
location /api/public-events/ {
    proxy_pass http://127.0.0.1:8788;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# retired poll UI -> canonical text observe
location = /public_showroom_poll.html {
    return 301 /public_observe_v1.html;
}
EOF
    echo "rewrote ${PUBLIC_SNIP}"
  fi
fi

sudo nginx -t
sudo systemctl reload nginx
echo "nginx reloaded: jemaai.cloud observe canonical"
