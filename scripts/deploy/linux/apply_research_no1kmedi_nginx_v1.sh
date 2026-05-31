#!/usr/bin/env bash
# research.no1kmedi.com static vhost (docroot /var/www/mkmlab).
set -euo pipefail

REPO_ROOT="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
EXAMPLE="$REPO_ROOT/scripts/deploy/linux/nginx-research-no1kmedi-com.conf.example"
SITE_AVAIL="/etc/nginx/sites-available/research.no1kmedi.com"
SITE_ENABLED="/etc/nginx/sites-enabled/research.no1kmedi.com"
RESEARCH_SSL_DIR="${RESEARCH_SSL_DIR:-/etc/letsencrypt/live/research.no1kmedi.com}"
DOCROOT="/var/www/mkmlab"

DO_APPLY=0
if [[ "${1:-}" == "-y" ]] || [[ "${1:-}" == "--apply" ]]; then
  DO_APPLY=1
fi

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing: $EXAMPLE" >&2
  exit 2
fi

mkdir -p "$DOCROOT"
cp -a "$EXAMPLE" "$SITE_AVAIL"
sed -i "s|/etc/letsencrypt/live/research.no1kmedi.com|${RESEARCH_SSL_DIR}|g" "$SITE_AVAIL"
ln -sf "$SITE_AVAIL" "$SITE_ENABLED"
echo "Installed research.no1kmedi.com -> $DOCROOT"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx 2>/dev/null || nginx -s reload
  echo "nginx reloaded"
else
  echo "Dry-run: run with -y after certbot for research.no1kmedi.com"
fi
