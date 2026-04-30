#!/usr/bin/env bash
# One-click PM2 health snapshot for bitcoin live app (VPS / Linux).
# Usage:
#   bash vps_pm2_bitcoin_live_health_snapshot.sh
#   PM2_APP_NAME=bitcoin-live-small-24h EXPECT_CWD_PREFIX=/opt/bitcoin-trading-live bash ...
# Optional: LOG_LINES=80 to tail recent logs; HEALTH_LOG=/path/to.log to append JSONL.

set -euo pipefail

PM2_APP_NAME="${PM2_APP_NAME:-bitcoin-live-small-24h}"
EXPECT_CWD_PREFIX="${EXPECT_CWD_PREFIX:-/opt/bitcoin-trading-live}"
LOG_LINES="${LOG_LINES:-80}"
HEALTH_LOG="${HEALTH_LOG:-}"

ts_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

if ! command -v pm2 >/dev/null 2>&1; then
  echo "[ERROR] pm2 not found in PATH" >&2
  exit 2
fi

if ! pm2 describe "$PM2_APP_NAME" >/dev/null 2>&1; then
  echo "[ERROR] pm2 app not found: $PM2_APP_NAME" >&2
  exit 2
fi

echo "=== PM2 health snapshot ==="
echo "time(UTC): $(ts_iso)"
echo "app: $PM2_APP_NAME"
echo "expected cwd prefix: $EXPECT_CWD_PREFIX"
echo

echo "--- pm2 describe (filtered) ---"
pm2 describe "$PM2_APP_NAME" 2>/dev/null | grep -E 'status|uptime|restart|script path|exec cwd|memory' || true
echo

VERDICT="GO"
REASONS=()

STATUS_LINE=$(pm2 describe "$PM2_APP_NAME" 2>/dev/null | grep -i 'status' | head -n1 || true)
if ! echo "$STATUS_LINE" | grep -qi 'online'; then
  VERDICT="WARN"
  REASONS+=("status line does not show online: ${STATUS_LINE:-<empty>}")
fi

CWD_LINE=$(pm2 describe "$PM2_APP_NAME" 2>/dev/null | grep -i 'exec cwd' | head -n1 || true)
if [[ -n "$CWD_LINE" ]] && ! echo "$CWD_LINE" | grep -q "$EXPECT_CWD_PREFIX"; then
  VERDICT="WARN"
  REASONS+=("exec cwd may not match $EXPECT_CWD_PREFIX: $CWD_LINE")
fi

SCRIPT_LINE=$(pm2 describe "$PM2_APP_NAME" 2>/dev/null | grep -i 'script path' | head -n1 || true)
if [[ -n "$SCRIPT_LINE" ]] && ! echo "$SCRIPT_LINE" | grep -q "$EXPECT_CWD_PREFIX"; then
  VERDICT="WARN"
  REASONS+=("script path may not match $EXPECT_CWD_PREFIX: $SCRIPT_LINE")
fi

if [[ ${#REASONS[@]} -gt 0 ]]; then
  echo "--- verdict: $VERDICT ---"
  for r in "${REASONS[@]}"; do
    echo "  - $r"
  done
else
  echo "--- verdict: $VERDICT ---"
fi
echo

if [[ -n "${LOG_LINES}" && "$LOG_LINES" != "0" ]]; then
  echo "--- pm2 logs (last $LOG_LINES lines, nostream) ---"
  pm2 logs "$PM2_APP_NAME" --nostream --lines "$LOG_LINES" 2>/dev/null || true
  echo
fi

if [[ -n "$HEALTH_LOG" ]]; then
  line=$(printf '{"ts":"%s","app":"%s","verdict":"%s"}\n' "$(ts_iso)" "$PM2_APP_NAME" "$VERDICT")
  mkdir -p "$(dirname "$HEALTH_LOG")" 2>/dev/null || true
  echo "$line" >>"$HEALTH_LOG" || true
  echo "[INFO] appended: $HEALTH_LOG"
fi

if [[ "$VERDICT" == "GO" ]]; then
  exit 0
fi
exit 1
