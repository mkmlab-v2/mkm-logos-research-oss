#!/bin/bash
# Sequential burn chain (Cloud Shell): wait wave3 -> wave4 gen-lang -> wave5 artful-athlete
set -euo pipefail
BURN_SH="$HOME/gcp_burn.sh"
CHAIN_LOG="$HOME/gcp_burn_chain.log"
exec >>"$CHAIN_LOG" 2>&1

echo "=== burn chain start $(date -u -Iseconds) ==="

wait_wave3() {
  while pgrep -f 'bash.*wave3_burn\.sh' >/dev/null 2>&1; do
    prog=$(grep '\[progress\]' "$HOME/wave3_burn.log" 2>/dev/null | tail -1 || true)
    echo "[chain] wave3 running ${prog:-no progress yet}"
    sleep 120
  done
  echo "[chain] wave3 process ended"
  grep 'DONE' "$HOME/wave3_burn.log" 2>/dev/null | tail -1 || echo "[chain] no DONE line in wave3 log"
}

run_wave() {
  local calls="$1" wave="$2" project="$3"
  echo "[chain] starting $wave calls=$calls project=$project"
  bash "$BURN_SH" "$calls" "$wave" "$project"
  echo "[chain] finished $wave exit=$?"
}

wait_wave3
run_wave 2000 wave4 gen-lang-client-0846393371
run_wave 2000 wave5 artful-athlete-490017-k3
echo "=== burn chain complete $(date -u -Iseconds) ==="
