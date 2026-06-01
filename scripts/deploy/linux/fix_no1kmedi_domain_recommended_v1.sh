#!/usr/bin/env bash
# Recommended no1kmedi nginx/SSL hygiene — SSOT mirror of Invoke-No1kmediDomainRecommendedSslFix inline body.
set -euo pipefail
REPO="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
log() { echo "[no1kmedi-recommended-fix] $*"; }
CLINIC_CERT="/etc/letsencrypt/live/clinic.no1kmedi.com/fullchain.pem"
if [[ -f "$CLINIC_CERT" ]]; then
  if ! openssl x509 -in "$CLINIC_CERT" -noout -text 2>/dev/null | grep -q 'www\.clinic\.no1kmedi\.com'; then
    certbot certonly --nginx -d clinic.no1kmedi.com -d www.clinic.no1kmedi.com --non-interactive --agree-tos -m admin@no1kmedi.com --expand || true
  fi
  bash "$REPO/scripts/deploy/linux/apply_clinic_no1kmedi_nginx_v1.sh" -y
fi
DISABLED_DIR="/etc/nginx/sites-disabled"
mkdir -p "$DISABLED_DIR"
disable_nginx_site() {
  local src="$1"
  [[ -e "$src" ]] || return 0
  local base dest
  base=$(basename "$src")
  dest="$DISABLED_DIR/$base"
  if [[ -e "$dest" ]]; then
    dest="$DISABLED_DIR/${base}.$(date +%Y%m%d%H%M%S)"
  fi
  mv "$src" "$dest" 2>/dev/null || rm -f "$src"
  log "Moved out of sites-enabled: $base -> $dest"
}
shopt -s nullglob
for stale in /etc/nginx/sites-enabled/*.legacy-disabled; do
  disable_nginx_site "$stale"
done
for legacy in /etc/nginx/sites-enabled/no1kmedi.com* /etc/nginx/sites-enabled/www.no1kmedi.com*; do
  base=$(basename "$legacy")
  [[ "$base" == "no1kmedi.com-portal" ]] && continue
  disable_nginx_site "$legacy"
done
if [[ -e /etc/nginx/sites-enabled/mkmlab-company-website ]]; then
  disable_nginx_site "/etc/nginx/sites-enabled/mkmlab-company-website"
  log "mkmlab-company-website removed (apex conflict with portal)"
fi
shopt -u nullglob
PORTAL_SSL_DIR="/etc/letsencrypt/live/no1kmedi.com"
if [[ ! -f "${PORTAL_SSL_DIR}/fullchain.pem" ]] && [[ -f /etc/letsencrypt/live/www.no1kmedi.com/fullchain.pem ]]; then
  PORTAL_SSL_DIR="/etc/letsencrypt/live/www.no1kmedi.com"
fi
if [[ -f "${PORTAL_SSL_DIR}/fullchain.pem" ]]; then
  export PORTAL_SSL_DIR
  bash "$REPO/scripts/deploy/linux/apply_no1kmedi_com_portal_nginx_v1.sh" -y
fi
nginx -t && (systemctl reload nginx 2>/dev/null || nginx -s reload)
log Done
