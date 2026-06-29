#!/bin/bash
# Productive GCP Free Trial burn — stop filler, run 4 B-track lanes from bundle.
set -euo pipefail
HOME_DIR="${HOME}"
BUNDLE="${HOME_DIR}/mkm_productive_burn_bundle_v1.json"
RUNNER="${HOME_DIR}/gcp_productive_burn_lane_runner_v1.py"
LOG_DIR="${HOME_DIR}/productive_burn_logs"
mkdir -p "$LOG_DIR"

echo "=== productive burn deploy $(date -u -Iseconds) ==="

# Stop filler / max parallel
for pat in wave3_burn gcp_max_burn gcp_max_after_wave3 gcp_burn_watchdog gcp_burn_phase2 'gcp_burn\.sh' gcp_burn_chain; do
  pkill -f "$pat" 2>/dev/null || true
done
sleep 2
echo "[deploy] filler processes stopped (or none)"

if [[ ! -f "$BUNDLE" ]]; then
  echo "MISSING bundle $BUNDLE — upload from local reports/sandbox/" >&2
  exit 1
fi
if [[ ! -f "$RUNNER" ]]; then
  echo "MISSING runner $RUNNER" >&2
  exit 1
fi

pip install -q google-genai

start_lane() {
  local lane="$1"
  local project="$2"
  local wave="$3"
  local out_jsonl="${LOG_DIR}/${lane}_${wave}.jsonl"
  local out_json="${LOG_DIR}/${lane}_${wave}_summary.json"
  if pgrep -f "gcp_productive_burn_lane_runner.*--lane ${lane}" >/dev/null 2>&1; then
    echo "[skip] lane $lane already running"
    return 0
  fi
  nohup python3 -u "$RUNNER" \
    --bundle "$BUNDLE" \
    --lane "$lane" \
    --project "$project" \
    --wave-id "$wave" \
    --out-jsonl "$out_jsonl" \
    --out-json "$out_json" \
    >>"${LOG_DIR}/${lane}_${wave}.log" 2>&1 &
  echo "[start] lane=$lane project=$project pid=$! log=${LOG_DIR}/${lane}_${wave}.log"
}

# gen-lang lanes
start_lane "asset_rag" "gen-lang-client-0846393371" "P3a_genlang"
start_lane "btrack_fills_daily" "gen-lang-client-0846393371" "P3b_fills"

# artful lanes (skip unless SKIP_CROSS_LENS unset and explicitly enabled)
if [[ "${SKIP_CROSS_LENS:-1}" != "1" ]]; then
  start_lane "cross_lens" "artful-athlete-490017-k3" "P3d_artful"
else
  echo "[skip] cross_lens artful (SKIP_CROSS_LENS=1 default)"
fi

# TruthfulQA handled separately if script present
if [[ -f "${HOME_DIR}/run_truthfulqa_vertex_ab_v1.py" ]]; then
  if ! pgrep -f run_truthfulqa_vertex_ab_v1.py >/dev/null 2>&1; then
    nohup python3 -u "${HOME_DIR}/run_truthfulqa_vertex_ab_v1.py" \
      --project artful-athlete-490017-k3 \
      --limit 120 \
      --out-json "${LOG_DIR}/truthfulqa_P3c_summary.json" \
      >>"${LOG_DIR}/truthfulqa_P3c.log" 2>&1 &
    echo "[start] truthfulqa pid=$!"
  fi
fi

echo "=== productive deploy done ==="
pgrep -af 'productive_burn|gcp_productive' || true
