#!/usr/bin/env bash
# Remote no1kmedi deploy steps (invoked via ssh). Args: vpsParent vpsDest vpsDestinyRepo tarRemote stamp
set -euo pipefail
vpsParent="${1:?}"
vpsDest="${2:?}"
vpsDestinyRepo="${3:?}"
tarRemote="${4:?}"
stamp="${5:?}"

mkdir -p "$vpsParent"
rm -rf "${vpsDest}.bak.${stamp}" 2>/dev/null || true
test -d "$vpsDest" && mv "$vpsDest" "${vpsDest}.bak.${stamp}" || true
mkdir -p "$vpsDest"
tar -xzf "$tarRemote" -C "$vpsParent"

ENV_FILE="$vpsDest/.env.local"
bak_env="${vpsDest}.bak.${stamp}/.env.local"
if [ -f "$bak_env" ]; then
  cp "$bak_env" "$ENV_FILE"
  echo "[no1kmedi-remote] restored .env.local from backup"
fi
touch "$ENV_FILE"
grep -q '^MKM_WORKSPACE_ROOT=' "$ENV_FILE" \
  && sed -i "s|^MKM_WORKSPACE_ROOT=.*|MKM_WORKSPACE_ROOT=${vpsDestinyRepo}|" "$ENV_FILE" \
  || echo "MKM_WORKSPACE_ROOT=${vpsDestinyRepo}" >> "$ENV_FILE"
grep -q '^KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN=' "$ENV_FILE" \
  || echo 'KM_PATIENT_CARE_BUNDLE_TRUST_SAME_ORIGIN=1' >> "$ENV_FILE"
grep -q '^MKM_PYTHON=' "$ENV_FILE" \
  && sed -i 's|^MKM_PYTHON=.*|MKM_PYTHON=/usr/bin/python3|' "$ENV_FILE" \
  || echo 'MKM_PYTHON=/usr/bin/python3' >> "$ENV_FILE"
grep -q '^LOGOS_STUDIO_EMBEDDING_SIDECAR=' "$ENV_FILE" \
  || echo 'LOGOS_STUDIO_EMBEDDING_SIDECAR=1' >> "$ENV_FILE"
grep -q '^LOGOS_STUDIO_EMBEDDING_SIDECAR_PORT=' "$ENV_FILE" \
  || echo 'LOGOS_STUDIO_EMBEDDING_SIDECAR_PORT=18765' >> "$ENV_FILE"
grep -q '^LOGOS_STUDIO_GRAPHRAG_ROUTER=' "$ENV_FILE" \
  || echo 'LOGOS_STUDIO_GRAPHRAG_ROUTER=1' >> "$ENV_FILE"
grep -q '^LOGOS_AGENT_AUTH_JWT_SECRET=' "$ENV_FILE" \
  || echo "LOGOS_AGENT_AUTH_JWT_SECRET=$(openssl rand -hex 32)" >> "$ENV_FILE"
grep -q '^NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED=' "$ENV_FILE" \
  || echo 'NEXT_PUBLIC_UNIVERSE_HUB_MKMLIFE_EMBED=1' >> "$ENV_FILE"
grep -q '^KM_CLINICIAN_PASTE_EXTRACT_LLM=' "$ENV_FILE" \
  && sed -i 's|^KM_CLINICIAN_PASTE_EXTRACT_LLM=.*|KM_CLINICIAN_PASTE_EXTRACT_LLM=1|' "$ENV_FILE" \
  || echo 'KM_CLINICIAN_PASTE_EXTRACT_LLM=1' >> "$ENV_FILE"
grep -q '^NEXT_PUBLIC_KM_CLINICIAN_PASTE_EXTRACT_LLM=' "$ENV_FILE" \
  && sed -i 's|^NEXT_PUBLIC_KM_CLINICIAN_PASTE_EXTRACT_LLM=.*|NEXT_PUBLIC_KM_CLINICIAN_PASTE_EXTRACT_LLM=1|' "$ENV_FILE" \
  || echo 'NEXT_PUBLIC_KM_CLINICIAN_PASTE_EXTRACT_LLM=1' >> "$ENV_FILE"
grep -q '^LOGOS_STUDIO_QUOTA_DISABLED=' "$ENV_FILE" \
  && sed -i 's|^LOGOS_STUDIO_QUOTA_DISABLED=.*|LOGOS_STUDIO_QUOTA_DISABLED=1|' "$ENV_FILE" \
  || echo 'LOGOS_STUDIO_QUOTA_DISABLED=1' >> "$ENV_FILE"

cd "$vpsDest" && npm ci && npm run build

if [ -f "$vpsDestinyRepo/scripts/logos_studio_embedding_sidecar_v1.py" ]; then
  if pm2 describe logos-embedding-sidecar >/dev/null 2>&1; then
    pm2 restart logos-embedding-sidecar --update-env || true
  else
    pm2 start "$vpsDestinyRepo/scripts/logos_studio_embedding_sidecar_v1.py" \
      --name logos-embedding-sidecar --interpreter /usr/bin/python3 --cwd "$vpsDestinyRepo" \
      -- --port 18765 --preload || true
  fi
fi
pm2 restart no1kmedi-com --update-env || pm2 start npm --name no1kmedi-com --cwd "$vpsDest" -- start
pm2 save
rm -f "$tarRemote"
