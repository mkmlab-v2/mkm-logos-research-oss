#!/usr/bin/env bash
set -euo pipefail

# Fetches Binance USDT-M fills into trades_*.json, then runs sync_cursor_trade_history_latest_24h.py.
# Requires API keys on the host (same as live trading).

TASK_NAME="bitcoin-binance-export-then-cursor-trade-history"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/root/projects/bitcoin-trading}"
EXPORT_SCRIPT="$WORKSPACE_ROOT/scripts/export_binance_fills_to_cursor_trade_history_v1.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCHEDULE="${SCHEDULE:-*/30 * * * *}"
LOG_PATH="${LOG_PATH:-/var/log/bitcoin_export_then_cursor_trade_history.log}"
EXPORT_HOURS="${EXPORT_HOURS:-168}"
SYNC_HOURS="${SYNC_HOURS:-24}"
# RUN_PROMOTION_GATE=1  -> add --run-promotion-gate
# EXPORT_TESTNET=1      -> add --testnet

if [[ ! -f "$EXPORT_SCRIPT" ]]; then
  echo "[ERROR] script not found: $EXPORT_SCRIPT" >&2
  exit 2
fi

CRON_CMD="cd \"$WORKSPACE_ROOT\" && \"$PYTHON_BIN\" \"$EXPORT_SCRIPT\" --hours \"$EXPORT_HOURS\" --run-sync --sync-hours \"$SYNC_HOURS\""
if [[ "${RUN_PROMOTION_GATE:-0}" == "1" ]]; then
  CRON_CMD+=" --run-promotion-gate"
fi
if [[ "${EXPORT_TESTNET:-0}" == "1" ]]; then
  CRON_CMD+=" --testnet"
fi
CRON_CMD+=" >> \"$LOG_PATH\" 2>&1"

CRON_LINE="$SCHEDULE $CRON_CMD # $TASK_NAME"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TASK_NAME" > "$TMP_CRON" || true
echo "$CRON_LINE" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[OK] cron registered: $TASK_NAME"
echo "schedule: $SCHEDULE"
echo "log:      $LOG_PATH"
echo "command:  $CRON_CMD"
