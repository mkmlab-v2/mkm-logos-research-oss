#!/usr/bin/env bash
# P0 Step 4: scoped pytest bundle (prophecy / dual-regime alignment).
# SSOT: docs/final/P0_COMMERCIALIZATION_TRACKER.md — Linux/macOS/CI twin of run_prophecy_alignment_pytest.ps1
# Do not run full-repo pytest from here; keep the file list explicit.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
WORKSPACE_ROOT="$(cd "${BT_ROOT}/../.." && pwd)"
cd "${BT_ROOT}"

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

# Fact-Lock SSOT: dual-regime smoke + multilens marginal harness V1. CI: .github/workflows/dual-regime-integrity.yml
"${PY}" -m pytest \
  tests/test_dual_regime_api_smoke.py \
  tests/test_multilens_marginal_utility_harness_v1.py \
  -v --tb=short
ec=$?
if [ "$ec" -ne 0 ]; then exit "$ec"; fi

cd "${WORKSPACE_ROOT}"
exec "${PY}" -m pytest \
  tests/test_add_entry16_source_and_rejudge.py \
  tests/test_logos_state_mapping_v1_snapshot.py \
  tests/test_cross_ref_dss_schema.py \
  tests/test_entry16_source_hunt_log.py \
  tests/test_entry16_source_hunt_summary.py \
  tests/test_entry16_promotion_gate.py \
  tests/test_waiting_queue_monthly_check_log.py \
  tests/test_btrack_phase3_snapshot_sync.py \
  tests/test_sasang_cross_ref_draft.py \
  tests/test_myeongni_16_state_transition_report.py \
  tests/test_myeongni_16_state_topflows_report.py \
  tests/test_myeongni_16_state_topflow_interpretation_report.py \
  tests/test_myeongni_topflow_integrated_report.py \
  tests/test_manse_precision_pointer.py \
  tests/test_manseryeok_provenance.py \
  tests/test_multilens_performance_eval_report.py \
  tests/test_multilens_performance_eval_report_v2.py \
  tests/test_multilens_eval_harness_v2_thin.py \
  tests/test_multilens_dual_regime_market_adapter_v1.py \
  tests/test_myeongni_insight_observation_log.py \
  -q --tb=short
