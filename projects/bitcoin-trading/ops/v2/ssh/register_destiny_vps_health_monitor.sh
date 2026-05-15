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
HEALTH_SCRIPT="projects/bitcoin-trading/src/monitoring/vps_health_monitor.py"
SNAPSHOT="projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh"
LEGACY_NAMES=(bitcoin-trading-health-monitor bitcoin-live-watchdog)
MISREGISTERED_NAMES=(pm2.ecosystem.destiny-health)

cd "$DESTINY_ROOT"

if ! command -v pm2 >/dev/null 2>&1; then
  echo "[ERROR] pm2 not in PATH" >&2
  exit 2
fi

if [[ ! -f "$HEALTH_SCRIPT" ]]; then
  echo "[ERROR] missing $DESTINY_ROOT/$HEALTH_SCRIPT — git pull or bundle sync first" >&2
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

PM2_ONLY="bitcoin-destiny-health-monitor"
export MKM_DESTINY_ROOT="$DESTINY_ROOT" PM2_LIVE_APP_NAME="$PM2_LIVE_APP_NAME"

for bad in "${MISREGISTERED_NAMES[@]}"; do
  if pm2 describe "$bad" >/dev/null 2>&1; then
    echo "[INFO] removing mis-registered PM2 app: $bad"
    pm2 delete "$bad" 2>/dev/null || true
  fi
done

if pm2 describe "$PM2_ONLY" >/dev/null 2>&1; then
  echo "[INFO] restarting $PM2_ONLY (--update-env)"
  pm2 restart "$PM2_ONLY" --update-env
else
  echo "[INFO] starting $PM2_ONLY (direct python entry)"
  pm2 start "$HEALTH_SCRIPT" \
    --name "$PM2_ONLY" \
    --cwd "$DESTINY_ROOT" \
    --interpreter python3 \
    --update-env \
    --env PYTHONUNBUFFERED=1 \
    --env PM2_PROCESS_NAME="$PM2_LIVE_APP_NAME" \
    --env VPS_HEALTH_CHECK_INTERVAL=60
fi

chmod +x "$SNAPSHOT" 2>/dev/null || true
echo
echo "[INFO] health snapshot (default destiny cwd prefix)"
bash "$SNAPSHOT" || true

pm2 save
echo "[OK] bitcoin-destiny-health-monitor registered; pm2 save done"
