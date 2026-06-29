#!/bin/bash
# Cloud Shell reconnect — watchdog + max burn deploy (no slow chain/phase2 restart).
set -euo pipefail
MARKER="$HOME/.gcp_burn_autoresume_last"
LOG="$HOME/gcp_burn_autoresume.log"
now=$(date -u +%s)
if [[ -f "$MARKER" ]]; then
  last=$(cat "$MARKER" 2>/dev/null || echo 0)
  if (( now - last < 120 )); then
    exit 0
  fi
fi
echo "$now" >"$MARKER"
{
  echo "[autoresume] $(date -u -Iseconds)"
  if grep -q 'STOP_BILLING_GUARD' "$HOME"/gcp_burn_*.log 2>/dev/null; then
    echo "[autoresume] billing guard tripped — skip restart"
    exit 0
  fi
  if [[ -x "$HOME/gcp_burn_watchdog.sh" ]] && ! pgrep -f 'gcp_burn_watchdog\.sh' >/dev/null 2>&1; then
    nohup bash "$HOME/gcp_burn_watchdog.sh" >>"$HOME/gcp_burn_watchdog_nohup.log" 2>&1 &
    echo "[autoresume] watchdog pid=$!"
  fi
  if [[ -x "$HOME/gcp_max_burn_deploy.sh" ]]; then
    nohup bash "$HOME/gcp_max_burn_deploy.sh" >>"$HOME/gcp_max_burn_deploy_nohup.log" 2>&1 &
    echo "[autoresume] max_burn_deploy pid=$!"
  fi
} >>"$LOG" 2>&1
