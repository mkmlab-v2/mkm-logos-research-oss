#!/bin/bash
# One-shot: billing-safe burn script + parallel max (artful now, dual after wave3).
set -euo pipefail
BURN="$HOME/gcp_burn.sh"
echo "=== max burn deploy $(date -u -Iseconds) ==="
# Stop slow sequential chain (replaced by parallel max)
pkill -f 'gcp_burn_chain\.sh' 2>/dev/null || true
pkill -f 'gcp_burn_phase2\.sh' 2>/dev/null || true
sleep 1
if pgrep -f 'wave3_burn\.sh' >/dev/null 2>&1; then
  echo "[deploy] wave3 still running — keep it"
else
  echo "[deploy] wave3 not running"
fi
# Parallel leg on artful NOW (gen-lang has wave3)
if ! pgrep -f 'gcp_burn\.sh.*artful-athlete' >/dev/null 2>&1; then
  nohup bash "$BURN" 5000 wave3p artful-athlete-490017-k3 >>"$HOME/gcp_burn_wave3p_nohup.log" 2>&1 &
  echo "[deploy] artful wave3p pid=$!"
else
  echo "[deploy] artful burn already running"
fi
# After wave3: dual parallel 6000 each (billing_guard inside burn.sh)
cat >"$HOME/gcp_max_after_wave3.sh" <<'EOS'
#!/bin/bash
set -euo pipefail
exec >>"$HOME/gcp_max_after_wave3.log" 2>&1
echo "wait wave3 $(date -u -Iseconds)"
while pgrep -f 'wave3_burn\.sh' >/dev/null 2>&1; do sleep 60; done
echo "wave3 ended $(date -u -Iseconds)"
bash "$HOME/gcp_max_burn_parallel.sh" 6000 max_gen max_art
echo "max_after_wave3 done $(date -u -Iseconds)"
EOS
chmod +x "$HOME/gcp_max_after_wave3.sh"
if ! pgrep -f 'gcp_max_after_wave3\.sh' >/dev/null 2>&1; then
  nohup bash "$HOME/gcp_max_after_wave3.sh" >>"$HOME/gcp_max_after_wave3_nohup.log" 2>&1 &
  echo "[deploy] max_after_wave3 pid=$!"
fi
echo "=== deploy done ==="
