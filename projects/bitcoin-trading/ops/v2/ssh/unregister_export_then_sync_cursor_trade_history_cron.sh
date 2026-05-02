#!/usr/bin/env bash
set -euo pipefail

TASK_NAME="bitcoin-binance-export-then-cursor-trade-history"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TASK_NAME" > "$TMP_CRON" || true
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[OK] cron unregistered: $TASK_NAME"
