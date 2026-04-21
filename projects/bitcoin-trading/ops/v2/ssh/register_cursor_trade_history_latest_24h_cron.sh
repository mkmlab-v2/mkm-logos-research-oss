#!/usr/bin/env bash
set -euo pipefail

# Registers a cron job that syncs cursor trade history and rebuilds latest window files.

TASK_NAME="bitcoin-cursor-trade-history-latest-24h"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/root/projects/bitcoin-trading}"
SCRIPT_PATH="$WORKSPACE_ROOT/scripts/sync_cursor_trade_history_latest_24h.py"
SOURCE_DIR="${SOURCE_DIR:-/root/projects/bitcoin-trading/exports/cursor_trade_history}"
DEST_DIR="${DEST_DIR:-/root/projects/bitcoin-trading/exports/cursor_trade_history}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCHEDULE="${SCHEDULE:-*/15 * * * *}"
LOG_PATH="${LOG_PATH:-/var/log/bitcoin_cursor_trade_history_latest_24h.log}"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "[ERROR] script not found: $SCRIPT_PATH" >&2
  exit 2
fi

CRON_CMD="cd \"$WORKSPACE_ROOT\" && \"$PYTHON_BIN\" \"$SCRIPT_PATH\" --source-dir \"$SOURCE_DIR\" --dest-dir \"$DEST_DIR\" >> \"$LOG_PATH\" 2>&1"
CRON_LINE="$SCHEDULE $CRON_CMD # $TASK_NAME"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TASK_NAME" > "$TMP_CRON" || true
echo "$CRON_LINE" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[OK] cron registered: $TASK_NAME"
echo "schedule: $SCHEDULE"
echo "command:  $CRON_CMD"
