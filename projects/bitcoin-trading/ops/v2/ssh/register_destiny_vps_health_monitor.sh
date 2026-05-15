#!/usr/bin/env bash
# Register PM2 health monitor on destiny monorepo (replaces legacy /opt/bitcoin-trading monitors).
#
# Usage (on VPS):
#   cd /opt/mkm-destiny-ai-41e38ec6
#   bash projects/bitcoin-trading/ops/v2/ssh/register_destiny_vps_health_monitor.sh
#
# Env:
#   MKM_DESTINY_ROOT  (default /opt/mkm-destiny-ai-41e38ec6)
#   PM2_LIVE_APP_NAME (default bitcoin-live-small-24h)

set -euo pipefail

DESTINY_ROOT="${MKM_DESTINY_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
PM2_LIVE_APP_NAME="${PM2_LIVE_APP_NAME:-bitcoin-live-small-24h}"
ECOSYSTEM="projects/bitcoin-trading/ops/pm2.ecosystem.destiny-health.cjs"
SNAPSHOT="projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh"
LEGACY_NAMES=(bitcoin-trading-health-monitor bitcoin-live-watchdog)

cd "$DESTINY_ROOT"

if ! command -v pm2 >/dev/null 2>&1; then
  echo "[ERROR] pm2 not in PATH" >&2
  exit 2
fi

if [[ ! -f "$ECOSYSTEM" ]]; then
  echo "[ERROR] missing $DESTINY_ROOT/$ECOSYSTEM — git pull or bundle sync first" >&2
  exit 2
fi

if ! pm2 describe "$PM2_LIVE_APP_NAME" >/dev/null 2>&1; then
  echo "[ERROR] live app not found: $PM2_LIVE_APP_NAME" >&2
  exit 2
fi

for legacy in "${LEGACY_NAMES[@]}"; do
  if pm2 describe "$legacy" >/dev/null 2>&1; then
    echo "[INFO] stopping legacy PM2 app: $legacy"
    pm2 stop "$legacy" 2>/dev/null || true
    pm2 delete "$legacy" 2>/dev/null || true
  fi
done

if pm2 describe bitcoin-destiny-health-monitor >/dev/null 2>&1; then
  echo "[INFO] reloading bitcoin-destiny-health-monitor"
  MKM_DESTINY_ROOT="$DESTINY_ROOT" PM2_LIVE_APP_NAME="$PM2_LIVE_APP_NAME" \
    pm2 reload "$ECOSYSTEM" --update-env
else
  echo "[INFO] starting bitcoin-destiny-health-monitor"
  MKM_DESTINY_ROOT="$DESTINY_ROOT" PM2_LIVE_APP_NAME="$PM2_LIVE_APP_NAME" \
    pm2 start "$ECOSYSTEM"
fi

chmod +x "$SNAPSHOT" 2>/dev/null || true
echo
echo "[INFO] health snapshot (default destiny cwd prefix)"
bash "$SNAPSHOT" || true

pm2 save
echo "[OK] bitcoin-destiny-health-monitor registered; pm2 save done"
