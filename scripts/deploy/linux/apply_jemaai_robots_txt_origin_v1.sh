#!/usr/bin/env bash
# jemaai.cloud: serve /robots.txt with HTTP 200 on :80 so CF prepends origin Disallow /legacy/.
set -euo pipefail

SITE="/etc/nginx/sites-enabled/jemaai.cloud"
ORIGIN_SNIP="/etc/nginx/snippets/jemaai_robots_txt_origin_v1.conf"
ORIGIN_SRC="${1:-/tmp/jemaai_robots_txt_origin_v1.conf}"
WEB_ROOT="${JEMAAI_WEB_ROOT:-/var/www/jemaai}"

if [[ ! -f "${SITE}" ]]; then
  echo "missing site: ${SITE}" >&2
  exit 1
fi
if [[ ! -f "${ORIGIN_SRC}" ]]; then
  echo "missing snippet source: ${ORIGIN_SRC}" >&2
  exit 1
fi
if [[ ! -f "${WEB_ROOT}/robots.txt" ]]; then
  echo "missing origin file: ${WEB_ROOT}/robots.txt" >&2
  exit 1
fi

BACKUP_DIR="/etc/nginx/sites-disabled"
sudo mkdir -p "${BACKUP_DIR}"
sudo cp -a "${SITE}" "${BACKUP_DIR}/$(basename "${SITE}").bak_robots_origin_v1_$(date +%Y%m%d%H%M%S)"
sudo install -m 0644 "${ORIGIN_SRC}" "${ORIGIN_SNIP}"
echo "installed ${ORIGIN_SNIP}"

if ! grep -q 'jemaai_robots_txt_origin_v1.conf' "${SITE}"; then
  sudo sed -i '/include \/etc\/nginx\/snippets\/jemaai_showroom_legacy_noindex_v1.conf;/a\    include /etc/nginx/snippets/jemaai_robots_txt_origin_v1.conf;' "${SITE}"
  echo "inserted TLS robots origin include"
fi

# Certbot :80 block returns 301 for all paths — CF origin probe needs 200 on /robots.txt.
if grep -q 'listen 80;' "${SITE}" && ! grep -q 'location = /robots.txt' "${SITE}"; then
  sudo tee "${SITE}.robots80.tmp" >/dev/null <<'EOF'
server {
    listen 80;
    server_name jemaai.cloud www.jemaai.cloud;

    location = /robots.txt {
        root /var/www/jemaai;
        default_type text/plain;
        add_header Cache-Control "public, max-age=300" always;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
EOF
  # Replace trailing certbot :80 server block (from "server {" with listen 80 through closing "}").
  python3 - "${SITE}" "${SITE}.robots80.tmp" <<'PY'
import re, sys
from pathlib import Path

site = Path(sys.argv[1])
new80 = Path(sys.argv[2]).read_text(encoding="utf-8")
text = site.read_text(encoding="utf-8")
pat = re.compile(
    r"server\s*\{\s*if\s*\(\$host\s*=\s*jemaai\.cloud\)\s*\{[^}]*\}\s*# managed by Certbot\s*"
    r"listen 80;\s*server_name jemaai\.cloud www\.jemaai\.cloud;\s*return 404;\s*# managed by Certbot\s*\}\s*",
    re.S,
)
if pat.search(text):
    text = pat.sub(new80 + "\n", text, count=1)
    site.write_text(text, encoding="utf-8")
    print("replaced certbot :80 block with robots.txt exception")
else:
    print("certbot :80 block not found or already patched — skip replace")
PY
  rm -f "${SITE}.robots80.tmp"
fi

sudo nginx -t
sudo systemctl reload nginx

curl -fsS --retry 3 --retry-delay 2 -H 'Host: jemaai.cloud' "http://127.0.0.1/robots.txt" | grep -q 'Disallow: /legacy/' \
  || { echo "local :80 robots check failed after reload" >&2; exit 1; }

echo "nginx reloaded: jemaai.cloud robots.txt origin probe OK"
