#!/usr/bin/env bash
set -euo pipefail

# Copy Fact-Safe risk profile from the monorepo (SSOT clone) into the lab-workspace
# clone used by PM2 when both trees exist on the same host (paths differ).
#
# Usage:
#   bash projects/bitcoin-trading/ops/v2/ssh/sync_fact_safe_risk_to_lab_workspace.sh
#   MKM_LAB_WORKSPACE_ROOT=/other/path bash .../sync_fact_safe_risk_to_lab_workspace.sh
#
# Env:
#   MKM_MONOREPO_ROOT   — default: /opt/mkm-monorepo
#   MKM_LAB_WORKSPACE_ROOT — default: /opt/mkm-lab-workspace-v2

MKM_MONOREPO_ROOT="${MKM_MONOREPO_ROOT:-/opt/mkm-monorepo}"
MKM_LAB_WORKSPACE_ROOT="${MKM_LAB_WORKSPACE_ROOT:-/opt/mkm-lab-workspace-v2}"

REL="projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"
SRC="${MKM_MONOREPO_ROOT%/}/${REL}"
DST="${MKM_LAB_WORKSPACE_ROOT%/}/${REL}"

if [[ ! -f "${SRC}" ]]; then
  echo "error: source missing: ${SRC}" >&2
  exit 1
fi

install -D -m 644 "${SRC}" "${DST}"

if cmp -s "${SRC}" "${DST}"; then
  echo "sync OK: ${DST}"
else
  echo "error: cmp mismatch after install" >&2
  exit 1
fi
