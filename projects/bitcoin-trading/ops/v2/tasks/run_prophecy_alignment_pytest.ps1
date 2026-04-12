# P0 Step 4: scoped pytest bundle (prophecy / dual-regime alignment).
# SSOT: docs/final/P0_COMMERCIALIZATION_TRACKER.md — use `py` only (not `python`).
# Do not run full-repo pytest from here; keep the file list explicit.

$ErrorActionPreference = 'Stop'

$btRoot = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
# bitcoin-trading -> projects -> repo root (matches run_prophecy_alignment_pytest.sh: BT_ROOT/../..)
$workspaceRoot = (Get-Item -LiteralPath $btRoot).Parent.Parent.FullName

# Fact-Lock SSOT: dual-regime smoke + multilens marginal harness V1 (bitcoin-trading/). CI: .github/workflows/dual-regime-integrity.yml
Set-Location -LiteralPath $btRoot
& py -m pytest 'tests/test_dual_regime_api_smoke.py' 'tests/test_multilens_marginal_utility_harness_v1.py' -v --tb=short
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
    'tests/test_manse_precision_pointer.py' `
    'tests/test_manseryeok_provenance.py' `
    'tests/test_multilens_performance_eval_report.py' `
    'tests/test_multilens_performance_eval_report_v2.py' `
    'tests/test_multilens_eval_harness_v2_thin.py' `
    'tests/test_multilens_dual_regime_market_adapter_v1.py' `
    'tests/test_myeongni_insight_observation_log.py' `
    'tests/test_spike_log_myeongri_correlation_v1.py' `
    'tests/test_convert_log_metabolism_to_myeongri_correlation_input_v1.py' `
    'tests/test_generate_log_metabolism_synthetic_cohort_v1.py' `
    'tests/test_gematria_myeongri_spike_smoke.py' `
    'tests/test_myeongri_fusion_scripts_smoke.py' `
    'tests/test_spike_4grid_myeongri_compression_v1.py' `
    'tests/test_hypothesis_insight_batch_v1_sample.py' `
    'tests/test_eval_prophecy_hit_rate_v1.py' `
    'tests/test_generate_btrack_hypothesis_prophecy_v1.py' `
    'tests/test_general_prophecy_schema_v1.py' `
    'tests/test_general_prophecy_chain_smoke.py' `
    'tests/test_resolve_general_prophecy_question_v1.py' `
    'tests/test_export_general_prophecy_to_jsonl.py' `
    -q --tb=short
exit $LASTEXITCODE
