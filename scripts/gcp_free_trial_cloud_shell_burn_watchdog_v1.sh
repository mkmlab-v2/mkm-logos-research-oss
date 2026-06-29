#!/bin/bash
# Poll every 5m: restart chain/phase2 if orchestrators died (wave3 burn untouched while running).
set -euo pipefail
LOG="$HOME/gcp_burn_watchdog.log"
INTERVAL="${WATCHDOG_INTERVAL_SEC:-300}"

tick() {
  echo "[watchdog] tick $(date -u -Iseconds)"
  if pgrep -f 'wave3_burn\.sh' >/dev/null 2>&1; then
    if ! pgrep -f 'gcp_burn_chain\.sh' >/dev/null 2>&1; then
      if ! grep -q 'burn chain complete' "$HOME/gcp_burn_chain.log" 2>/dev/null; then
        nohup bash "$HOME/gcp_burn_chain.sh" >>"$HOME/gcp_burn_chain_nohup.log" 2>&1 &
        echo "[watchdog] restarted gcp_burn_chain.sh pid=$!"
      fi
    fi
  fi
  if grep -q 'STOP_BILLING_GUARD' "$HOME"/gcp_burn_*.log 2>/dev/null; then
    echo "[watchdog] STOP_BILLING_GUARD seen — no restart (avoid extra billing)"
  elif [[ -x "$HOME/gcp_max_burn_deploy.sh" ]] && ! pgrep -f 'gcp_burn\.sh' >/dev/null 2>&1; then
    if ! grep -q 'deploy done' "$HOME/gcp_max_burn_parallel.log" 2>/dev/null; then
      if ! pgrep -f 'wave3_burn\.sh' >/dev/null 2>&1 && ! pgrep -f 'gcp_max_after_wave3' >/dev/null 2>&1; then
        echo "[watchdog] idle after wave3 — skip auto (manual max deploy)"
      fi
    fi
  fi
  prog=$(grep '\[progress\]' "$HOME/wave3_burn.log" 2>/dev/null | tail -1 || true)
  echo "[watchdog] wave3_progress=${prog:-none}"
}

exec >>"$LOG" 2>&1
echo "[watchdog] start $(date -u -Iseconds) interval=${INTERVAL}s"
while true; do
  tick || echo "[watchdog] tick error $?"
  sleep "$INTERVAL"
done
