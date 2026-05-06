#!/usr/bin/env bash
set -euo pipefail

TASK_SOFT="agct-locked-baseline-soft"
TASK_STRICT="agct-locked-baseline-strict"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -Ev "$TASK_SOFT|$TASK_STRICT" > "$TMP_CRON" || true
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[OK] cron unregistered: $TASK_SOFT / $TASK_STRICT"
