#!/usr/bin/env bash
# Idempotent Cloud Agent update script (runs from repo root on VM boot).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "[mkm-cloud-install] workspace=${ROOT}"

python3 -m pip install -q --break-system-packages pytest jsonschema tiktoken 2>/dev/null \
  || python3 -m pip install -q pytest jsonschema tiktoken

# Thin gate: GitHub destiny is not a full monorepo mirror (weather/local artifacts absent).
# Do not call verify_p0_constitution_gate_paths_cloud_v1.py here.
python3 scripts/verify_mkm_cloud_agent_env_ready_v1.py

echo "[mkm-cloud-install] OK"
