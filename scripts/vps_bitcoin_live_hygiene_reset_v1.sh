#!/usr/bin/env bash
# Run ON VPS via: ssh vps-mkmlife 'bash -s' < scripts/vps_bitcoin_live_hygiene_reset_v1.sh
# Or: ssh vps-mkmlife "bash -s" < scripts/vps_bitcoin_live_hygiene_reset_v1.sh
set -euo pipefail

LIVE="/opt/bitcoin-trading-live"
REAL="$(readlink -f "$LIVE")"
echo "REAL=$REAL"

mkdir -p /var/backups/mkm-hygiene-20260512
if [[ -d "$REAL/reports/_recovered_bad_path_20260512" ]]; then
  mv -v "$REAL/reports/_recovered_bad_path_20260512" /var/backups/mkm-hygiene-20260512/
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BK="/var/backups/bitcoin-trading-wt-${STAMP}.tar.gz"
echo "BACKUP=$BK"
tar czf "$BK" -C "$REAL" .
ls -lh "$BK"

cd "$LIVE"
git fetch origin -q
git reset --hard origin/main
git clean -fd

echo "--- git status ---"
git status -sb
git log -1 --oneline

pm2 restart bitcoin-live-small-24h --update-env || true
echo "--- pm2 (first lines) ---"
pm2 describe bitcoin-live-small-24h 2>/dev/null | head -n 14 || true
