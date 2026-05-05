#!/usr/bin/env bash
# Run health snapshot N times with a fixed interval (default: 3 rounds, 30 minutes).
# Same env vars as vps_pm2_bitcoin_live_health_snapshot.sh (PM2_APP_NAME, EXPECT_CWD_PREFIX, ...).
#
# Usage:
#   bash vps_pm2_bitcoin_live_drift_watch.sh
#   ROUNDS=2 INTERVAL_SEC=1800 bash vps_pm2_bitcoin_live_drift_watch.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROUNDS="${ROUNDS:-3}"
INTERVAL_SEC="${INTERVAL_SEC:-1800}"

echo "[INFO] rounds=$ROUNDS interval_sec=$INTERVAL_SEC (UTC times below)"
for i in $(seq 1 "$ROUNDS"); do
  echo
  echo "########## drift round $i / $ROUNDS ##########"
  bash "$DIR/vps_pm2_bitcoin_live_health_snapshot.sh" || true
  if [[ "$i" -lt "$ROUNDS" ]]; then
    echo "[INFO] sleeping ${INTERVAL_SEC}s until next round..."
    sleep "$INTERVAL_SEC"
  fi
done
echo
echo "[DONE] drift watch complete."
