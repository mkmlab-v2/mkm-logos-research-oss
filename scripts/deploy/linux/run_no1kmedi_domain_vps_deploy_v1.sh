#!/usr/bin/env bash
# VPS one-shot: research + clinic + portal nginx, certbot (best-effort), mkmlab 301, pm2 restart.
set -euo pipefail

REPO="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
cd "$REPO"

APPLY="${1:---apply}"
DO_APPLY=0
[[ "$APPLY" == "-y" ]] || [[ "$APPLY" == "--apply" ]] && DO_APPLY=1

log() { echo "[no1kmedi-domain-deploy] $*"; }

if [[ ! -d "$REPO/scripts/deploy/linux" ]]; then
  echo "Missing $REPO — set MKM_REPO_ROOT" >&2
  exit 2
fi

APEX_SSL="/etc/letsencrypt/live/no1kmedi.com/fullchain.pem"
# Any enabled vhost pointing at missing apex cert breaks nginx -t for the whole host.
if [[ ! -f "$APEX_SSL" ]] && [[ "$DO_APPLY" -eq 1 ]]; then
  for f in /etc/nginx/sites-enabled/*; do
    [[ -e "$f" ]] || continue
    if grep -q 'letsencrypt/live/no1kmedi.com/fullchain' "$f" 2>/dev/null; then
      rm -f "$f"
      log "Removed broken site (no apex cert): $f"
    fi
  done
  if [[ -L /etc/nginx/sites-enabled/no1kmedi.com ]]; then
    mv /etc/nginx/sites-enabled/no1kmedi.com /etc/nginx/sites-enabled/no1kmedi.com.legacy-disabled 2>/dev/null \
      || rm -f /etc/nginx/sites-enabled/no1kmedi.com
    log "Disabled legacy sites-enabled/no1kmedi.com"
  fi
fi

# Bootstrap HTTP-only research if no cert yet (certbot --nginx needs reachable :80)
RESEARCH_SSL="/etc/letsencrypt/live/research.no1kmedi.com/fullchain.pem"
if [[ ! -f "$RESEARCH_SSL" ]]; then
  log "Bootstrap research.no1kmedi.com HTTP-only for certbot"
  tee /etc/nginx/sites-available/research.no1kmedi.com.bootstrap >/dev/null <<'BOOT'
server {
    listen 80;
    listen [::]:80;
    server_name research.no1kmedi.com;
    root /var/www/mkmlab;
    index index.html en.html;
    location / { try_files $uri $uri/ =404; }
}
BOOT
  ln -sf /etc/nginx/sites-available/research.no1kmedi.com.bootstrap /etc/nginx/sites-enabled/research.no1kmedi.com.bootstrap
  if [[ "$DO_APPLY" -eq 1 ]]; then nginx -t && systemctl reload nginx; fi
  if [[ "$DO_APPLY" -eq 1 ]]; then
    certbot certonly --nginx -d research.no1kmedi.com --non-interactive --agree-tos -m admin@no1kmedi.com || log "WARN: certbot research failed"
  fi
  rm -f /etc/nginx/sites-enabled/research.no1kmedi.com.bootstrap
fi

run_apply() {
  local script="$1"
  if [[ "$DO_APPLY" -eq 1 ]]; then
    bash "$script" -y
  else
    bash "$script"
  fi
}

run_apply "$REPO/scripts/deploy/linux/apply_research_no1kmedi_nginx_v1.sh"

CLINIC_SSL="/etc/letsencrypt/live/clinic.no1kmedi.com/fullchain.pem"
if [[ ! -f "$CLINIC_SSL" ]] && [[ "$DO_APPLY" -eq 1 ]]; then
  certbot certonly --nginx -d clinic.no1kmedi.com -d www.clinic.no1kmedi.com \
    --non-interactive --agree-tos -m admin@no1kmedi.com || log "WARN: certbot clinic failed"
fi
run_apply "$REPO/scripts/deploy/linux/apply_clinic_no1kmedi_nginx_v1.sh"

if [[ ! -f "$APEX_SSL" ]] && [[ "$DO_APPLY" -eq 1 ]]; then
  log "Bootstrap no1kmedi.com HTTP-only portal for certbot"
  bash "$REPO/scripts/deploy/linux/apply_no1kmedi_com_portal_http_only_v1.sh" -y || log "WARN: HTTP portal bootstrap failed"
  certbot certonly --nginx -d no1kmedi.com -d www.no1kmedi.com \
    --non-interactive --agree-tos -m admin@no1kmedi.com || log "WARN: certbot apex failed (DNS or :80 conflict)"
fi
if [[ -f "$APEX_SSL" ]]; then
  run_apply "$REPO/scripts/deploy/linux/apply_no1kmedi_com_portal_nginx_v1.sh"
else
  log "WARN: no apex cert — keeping HTTP-only portal (HTTPS redirect after certbot)"
  if [[ "$DO_APPLY" -eq 1 ]]; then
    bash "$REPO/scripts/deploy/linux/apply_no1kmedi_com_portal_http_only_v1.sh" -y || true
  fi
fi

run_apply "$REPO/scripts/deploy/linux/apply_mkmlab_space_retire_301_v1.sh"

if [[ "$DO_APPLY" -eq 1 ]]; then
  nginx -t
  systemctl reload nginx
  if command -v pm2 >/dev/null 2>&1; then
    pm2 restart no1kmedi-com || pm2 restart all --update-env || true
    log "pm2 restart no1kmedi-com done"
  fi
fi

log "Done (apply=$DO_APPLY)"
