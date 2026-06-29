#!/bin/bash
# One-shot overnight burn on browser Cloud Shell — no ADC file required if gcloud user is ACTIVE.
set -euo pipefail
HOME_DIR="${HOME}"
RUNNER="${HOME_DIR}/gcp_productive_burn_lane_runner_v1.py"
BUNDLE="${HOME_DIR}/mkm_productive_burn_bundle_v1.json"
LOG_DIR="${HOME_DIR}/productive_burn_logs"
ARCHIVE="${LOG_DIR}/archive_pre_unattended"
WAVE_TAG="P6"
PROJECT="gen-lang-client-0846393371"

gcloud config set project "$PROJECT" >/dev/null
ACTIVE="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1 || true)"
if [[ -z "$ACTIVE" ]]; then
  echo "STOP: no ACTIVE gcloud account. In browser Console open Cloud Shell while logged in as jema12." >&2
  exit 1
fi
echo "[unattended] account=$ACTIVE project=$PROJECT"

ADC="${HOME}/.config/gcloud/application_default_credentials.json"
if [[ -f "$ADC" ]]; then
  export GOOGLE_APPLICATION_CREDENTIALS="$ADC"
  export GOOGLE_CLOUD_QUOTA_PROJECT="$PROJECT"
fi

pip install -q google-genai google-auth

python3 -u "$RUNNER" \
  --bundle "$BUNDLE" --lane asset_rag --project "$PROJECT" \
  --wave-id "${WAVE_TAG}_smoke" --start-index 1 --dry-run >/dev/null 2>&1 || true

python3 - <<'PY' || { echo "STOP: Vertex smoke failed — check IAM / account"; exit 1; }
import subprocess, sys
from google import genai
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location(
    "runner", Path.home() / "gcp_productive_burn_lane_runner_v1.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
creds, mode = mod._load_vertex_credentials()
print("[smoke] auth", mode, file=sys.stderr)
client = genai.Client(
    vertexai=True, project="gen-lang-client-0846393371", location="us-central1", credentials=creds
)
r = client.models.generate_content(model="gemini-2.5-pro", contents="[HYPO] OK")
print("[smoke] vertex", (getattr(r, "text", None) or str(r))[:60])
PY

mkdir -p "$LOG_DIR" "$ARCHIVE"
pkill -f gcp_productive_burn_lane_runner 2>/dev/null || true
sleep 2

shopt -s nullglob
for f in "${LOG_DIR}"/*_P4a_genlang* "${LOG_DIR}"/*_P4b_fills* \
         "${LOG_DIR}"/*_P5a_genlang* "${LOG_DIR}"/*_P5b_fills*; do
  [[ -e "$f" ]] || continue
  echo "[archive] $f"
  mv -f "$f" "$ARCHIVE/"
done
shopt -u nullglob

start_lane() {
  local lane="$1" wave="$2"
  local out_jsonl="${LOG_DIR}/${lane}_${wave}.jsonl"
  local out_json="${LOG_DIR}/${lane}_${wave}_summary.json"
  nohup python3 -u "$RUNNER" \
    --bundle "$BUNDLE" --lane "$lane" --project "$PROJECT" \
    --wave-id "$wave" --start-index 1 \
    --out-jsonl "$out_jsonl" --out-json "$out_json" \
    >>"${LOG_DIR}/${lane}_${wave}.log" 2>&1 &
  echo "[start] pid=$! lane=$lane wave=$wave log=${LOG_DIR}/${lane}_${wave}.log"
}

echo "=== unattended ${WAVE_TAG} $(date -u -Iseconds) ==="
start_lane "asset_rag" "${WAVE_TAG}a_genlang"
start_lane "btrack_fills_daily" "${WAVE_TAG}b_fills"
echo "Monitor: tail -f ${LOG_DIR}/asset_rag_${WAVE_TAG}a_genlang.log"
pgrep -af gcp_productive_burn_lane_runner || true
