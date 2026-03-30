#!/usr/bin/env bash
# P0 Step 4: scoped pytest bundle (prophecy / dual-regime alignment).
# SSOT: docs/final/P0_COMMERCIALIZATION_TRACKER.md — Linux/macOS/CI twin of run_prophecy_alignment_pytest.ps1
# Do not run full-repo pytest from here; keep the file list explicit.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORKSPACE_ROOT="$(cd "${BT_ROOT}/../.." && pwd)"
cd "${BT_ROOT}"

# Fact-Lock SSOT: dual-regime smoke (13 cases). CI: .github/workflows/dual-regime-integrity.yml
TEST_FILES=(
  "tests/test_dual_regime_api_smoke.py"
)

# Prefer project .venv (WSL PEP 668–safe local pytest). GitHub Actions uses setup-python + pip; no .venv there.
if [ -x "${BT_ROOT}/.venv/bin/python" ]; then
  PY="${BT_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "error: python3 or python not found (optional: python3 -m venv .venv && .venv/bin/pip install pytest)" >&2
  exit 127
fi

"${PY}" -m pytest "${TEST_FILES[@]}" -v --tb=short
ec=$?
if [ "$ec" -ne 0 ]; then exit "$ec"; fi

cd "${WORKSPACE_ROOT}"
exec "${PY}" -m pytest tests/test_logos_state_mapping_v1_snapshot.py tests/test_cross_ref_dss_schema.py -q --tb=short
