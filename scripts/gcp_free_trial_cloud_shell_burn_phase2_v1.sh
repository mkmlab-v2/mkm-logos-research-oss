#!/bin/bash
# Runs after gcp_burn_chain.sh + all gcp_burn.sh children finish.
set -euo pipefail
exec >>"$HOME/gcp_burn_phase2.log" 2>&1
echo "phase2 wait $(date -u -Iseconds)"
while pgrep -f 'gcp_burn_chain\.sh' >/dev/null; do sleep 180; done
while pgrep -f 'bash.*gcp_burn\.sh' >/dev/null; do sleep 180; done
echo "phase2 burn $(date -u -Iseconds)"
bash "$HOME/gcp_burn.sh" 3000 wave6 gen-lang-client-0846393371
bash "$HOME/gcp_burn.sh" 3000 wave7 artful-athlete-490017-k3
echo "phase2 done $(date -u -Iseconds)"
