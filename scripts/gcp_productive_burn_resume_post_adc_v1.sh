#!/bin/bash
# After: gcloud auth login + gcloud auth application-default login (jema12).
# Archives failed P4 (metadata ADC) and starts P5 fresh.
set -euo pipefail
HOME_DIR="${HOME}"
RUNNER="${HOME_DIR}/gcp_productive_burn_lane_runner_v1.py"
BUNDLE="${HOME_DIR}/mkm_productive_burn_bundle_v1.json"
LOG_DIR="${HOME_DIR}/productive_burn_logs"
ARCHIVE="${LOG_DIR}/archive_p4_metadata_adc_fail"

ADC="${HOME}/.config/gcloud/application_default_credentials.json"
ACTIVE="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1 || true)"
if [[ -f "$ADC" ]]; then
  export GOOGLE_APPLICATION_CREDENTIALS="$ADC"
  export GOOGLE_CLOUD_QUOTA_PROJECT="gen-lang-client-0846393371"
  echo "[auth] adc_file"
elif [[ -n "$ACTIVE" ]]; then
  echo "[auth] gcloud_cli_token account=$ACTIVE (no ADC file)"
else
  echo "STOP: need ACTIVE gcloud user OR application-default login" >&2
  exit 1
fi

mkdir -p "$LOG_DIR" "$ARCHIVE"
pkill -f gcp_productive_burn_lane_runner 2>/dev/null || true
sleep 2

shopt -s nullglob
for f in "${LOG_DIR}"/*_P4a_genlang* "${LOG_DIR}"/*_P4b_fills*; do
  [[ -e "$f" ]] || continue
  echo "[archive] $f"
  mv -f "$f" "$ARCHIVE/"
done
shopt -u nullglob

pip install -q google-genai google-auth

start_lane() {
  local lane="$1" wave="$2"
  local out_jsonl="${LOG_DIR}/${lane}_${wave}.jsonl"
  local out_json="${LOG_DIR}/${lane}_${wave}_summary.json"
  echo "[p5] lane=$lane wave=$wave"
  nohup python3 -u "$RUNNER" \
    --bundle "$BUNDLE" --lane "$lane" --project gen-lang-client-0846393371 \
    --wave-id "$wave" --start-index 1 \
    --out-jsonl "$out_jsonl" --out-json "$out_json" \
    >>"${LOG_DIR}/${lane}_${wave}.log" 2>&1 &
  echo "[start] pid=$! $lane $wave"
}

echo "=== P5 post-ADC $(date -u -Iseconds) ==="
start_lane "asset_rag" "P5a_genlang"
start_lane "btrack_fills_daily" "P5b_fills"
pgrep -af gcp_productive_burn_lane_runner || true
