#!/usr/bin/env bash
set -euo pipefail

# Register cron for factor influence latest refresh.

TASK_NAME="bitcoin-factor-influence-latest"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/mkm-lab-workspace-v2/projects/bitcoin-trading}"
SCRIPT_PATH="$WORKSPACE_ROOT/scripts/report_factor_influence_latest.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCHEDULE="${SCHEDULE:-*/30 * * * *}"
LOG_FILE="${LOG_FILE:-/root/.pm2/logs/bitcoin-live-out.log}"
OUT_DIR="${OUT_DIR:-$WORKSPACE_ROOT/exports/cursor_trade_history}"
RUN_LOG="${RUN_LOG:-$WORKSPACE_ROOT/logs/factor_influence_cron.log}"
RECENT_LINES="${RECENT_LINES:-1200}"
WINDOW_HOURS="${WINDOW_HOURS:-24}"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "[ERROR] script not found: $SCRIPT_PATH" >&2
  exit 2
fi

CRON_CMD="cd \"$WORKSPACE_ROOT\" && mkdir -p \"$WORKSPACE_ROOT/logs\" && \"$PYTHON_BIN\" \"$SCRIPT_PATH\" --log-file \"$LOG_FILE\" --out-dir \"$OUT_DIR\" --recent-lines \"$RECENT_LINES\" --window-hours \"$WINDOW_HOURS\" --emit-legacy-files >> \"$RUN_LOG\" 2>&1"
CRON_LINE="$SCHEDULE $CRON_CMD # $TASK_NAME"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TASK_NAME" > "$TMP_CRON" || true
echo "$CRON_LINE" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[OK] cron registered: $TASK_NAME"
echo "schedule: $SCHEDULE"
echo "command:  $CRON_CMD"
