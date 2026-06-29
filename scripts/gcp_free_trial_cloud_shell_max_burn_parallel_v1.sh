#!/bin/bash
# Max burn: parallel on BOTH Free Trial projects. Stops on billing_guard in logs.
set -euo pipefail
LOG="$HOME/gcp_max_burn_parallel.log"
BURN="$HOME/gcp_burn.sh"
P1="gen-lang-client-0846393371"
P2="artful-athlete-490017-k3"
CALLS_EACH="${1:-5000}"
WAVE_P1="${2:-max_p1}"
WAVE_P2="${3:-max_p2}"
exec >>"$LOG" 2>&1

echo "=== max parallel burn start $(date -u -Iseconds) calls_each=$CALLS_EACH ==="

wait_if_running() {
  local pat="$1"
  while pgrep -f "$pat" >/dev/null 2>&1; do
    echo "[max] waiting $pat"
    sleep 120
  done
}

# Let existing wave3 on gen-lang finish if still on old script name
wait_if_running 'wave3_burn\.sh'

echo "[max] launching parallel burns"
nohup bash "$BURN" "$CALLS_EACH" "$WAVE_P1" "$P1" >>"$HOME/gcp_burn_${WAVE_P1}_nohup.log" 2>&1 &
pid1=$!
nohup bash "$BURN" "$CALLS_EACH" "$WAVE_P2" "$P2" >>"$HOME/gcp_burn_${WAVE_P2}_nohup.log" 2>&1 &
pid2=$!
echo "[max] pids p1=$pid1 p2=$pid2"

wait "$pid1" || true
wait "$pid2" || true
echo "=== max parallel burn end $(date -u -Iseconds) ==="
