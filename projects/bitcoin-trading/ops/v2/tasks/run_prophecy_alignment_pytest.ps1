# P0 Step 4: scoped pytest bundle (prophecy / dual-regime alignment).
# SSOT: docs/final/P0_COMMERCIALIZATION_TRACKER.md — use `py` only (not `python`).
# Do not run full-repo pytest from here; keep the file list explicit.

$ErrorActionPreference = 'Stop'

$btRoot = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
# bitcoin-trading -> projects -> repo root (matches run_prophecy_alignment_pytest.sh: BT_ROOT/../..)
$workspaceRoot = (Get-Item -LiteralPath $btRoot).Parent.Parent.FullName

# Fact-Lock SSOT: dual-regime smoke (14 cases). CI: .github/workflows/dual-regime-integrity.yml
Set-Location -LiteralPath $btRoot
& py -m pytest 'tests/test_dual_regime_api_smoke.py' -v --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Workspace-root Fact-Lock (logos snapshot + CROSS_REF join); mirrors CI steps after prophecy bundle.
Set-Location -LiteralPath $workspaceRoot
& py -m pytest `
    'tests/test_add_entry16_source_and_rejudge.py' `
    'tests/test_logos_state_mapping_v1_snapshot.py' `
    'tests/test_cross_ref_dss_schema.py' `
    'tests/test_entry16_source_hunt_log.py' `
    'tests/test_entry16_source_hunt_summary.py' `
    'tests/test_entry16_promotion_gate.py' `
    'tests/test_waiting_queue_monthly_check_log.py' `
    'tests/test_btrack_phase3_snapshot_sync.py' `
    'tests/test_sasang_cross_ref_draft.py' `
    'tests/test_myeongni_16_state_transition_report.py' `
    'tests/test_myeongni_16_state_topflows_report.py' `
    'tests/test_myeongni_16_state_topflow_interpretation_report.py' `
    'tests/test_myeongni_topflow_integrated_report.py' `
    'tests/test_multilens_performance_eval_report.py' `
    'tests/test_multilens_performance_eval_report_v2.py' `
    'tests/test_myeongni_insight_observation_log.py' `
    -q --tb=short
exit $LASTEXITCODE
