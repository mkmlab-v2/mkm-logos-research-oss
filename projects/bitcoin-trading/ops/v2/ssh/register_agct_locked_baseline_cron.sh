#!/usr/bin/env bash
set -euo pipefail

TASK_SOFT="agct-locked-baseline-soft"
TASK_STRICT="agct-locked-baseline-strict"

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/mkm-lab-workspace-v2}"
SOFT_SCRIPT="${SOFT_SCRIPT:-$WORKSPACE_ROOT/scripts/run_agct_locked_baseline_cron_soft.sh}"
STRICT_SCRIPT="${STRICT_SCRIPT:-$WORKSPACE_ROOT/scripts/run_agct_locked_baseline_cron_strict.sh}"

SOFT_SCHEDULE="${SOFT_SCHEDULE:-12 0 * * *}"
STRICT_SCHEDULE="${STRICT_SCHEDULE:-42 0 * * 1}"

SOFT_LOG_PATH="${SOFT_LOG_PATH:-$WORKSPACE_ROOT/logs/agct_locked_baseline_soft_cron.log}"
STRICT_LOG_PATH="${STRICT_LOG_PATH:-$WORKSPACE_ROOT/logs/agct_locked_baseline_strict_cron.log}"

if [[ ! -f "$SOFT_SCRIPT" ]]; then
  echo "[ERROR] soft script not found: $SOFT_SCRIPT" >&2
  exit 2
fi
if [[ ! -f "$STRICT_SCRIPT" ]]; then
  echo "[ERROR] strict script not found: $STRICT_SCRIPT" >&2
  exit 2
fi

mkdir -p "$(dirname "$SOFT_LOG_PATH")" "$(dirname "$STRICT_LOG_PATH")"

CRON_LINE_SOFT="$SOFT_SCHEDULE $SOFT_SCRIPT >> $SOFT_LOG_PATH 2>&1 # $TASK_SOFT"
CRON_LINE_STRICT="$STRICT_SCHEDULE $STRICT_SCRIPT >> $STRICT_LOG_PATH 2>&1 # $TASK_STRICT"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -Ev "$TASK_SOFT|$TASK_STRICT" > "$TMP_CRON" || true
echo "$CRON_LINE_SOFT" >> "$TMP_CRON"
echo "$CRON_LINE_STRICT" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[OK] cron registered: $TASK_SOFT / $TASK_STRICT"
echo "soft_schedule:   $SOFT_SCHEDULE"
echo "strict_schedule: $STRICT_SCHEDULE"
echo "soft_log:        $SOFT_LOG_PATH"
echo "strict_log:      $STRICT_LOG_PATH"
