param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$required = @(
    "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs\final\MKM12_PRISM_INDEX_REGISTRY_V1.json",
    "docs\final\P0_COMMERCIALIZATION_TRACKER.md",
    "docs\final\COMPRESSION_SLA_POLICY_V1.md",
    "docs\final\COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs\final\BENCH_L1_API_LOAD_VPS_RUNBOOK.md",
    "docs\NotebookLM_sources_manifest.md",
    ".cursorrules",
    "AGENTS.md",
    "projects\bitcoin-trading\AGENTS.md",
    "CLAUDE.md",
    "docs\final\LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md",
    "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1",
    "scripts\run_waiting_queue_monthly_check.ps1",
    "scripts\eval_prophecy_hit_rate_v1.py",
    "scripts\fetch_kospi_yfinance_csv.py",
    "tests\test_load_kospi_yf_rows.py",
    "docs\final\GENERAL_PROPHECY_SCHEMA_V1.json",
    "scripts\generate_general_prophecy_v1.py",
    "scripts\build_general_prophecy_brief.py",
    "scripts\eval_general_prophecy_brier_score.py",
    "scripts\resolve_general_prophecy_question_v1.py",
    "tests\fixtures\general_prophecy_registry_sample_v1.json",
    "tests\fixtures\general_prophecy_registry_seed_5_v1.json",
    "tests\fixtures\general_prophecy_registry_brier_smoke_v1.json",
    "tests\fixtures\general_prophecy_registry_official_seed_v1.json",
    "tests\fixtures\general_prophecy_registry_macro_h2_2026_pack_v1.json",
    "scripts\generate_btrack_hypothesis_prophecy_v1.py",
    "scripts\build_logos_wide_restoration.py",
    "scripts\build_btrack_prophecy_score_from_ohlcv.py",
    "scripts\run_daily_prophecy_eval_and_report.ps1",
    "scripts\report_btrack_notebooklm_jsonl_kpi.py",
    "projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1",
    "scripts\core\domain_router.py",
    "codebook\shards\zone_a_scm.json",
    "codebook\shards\zone_b_timing.json",
    "codebook\shards\zone_c_hangul.json",
    "codebook\shards\zone_d_ssot.json",
    "codebook\shards\zone_e_finance.json",
    "codebook\shards\zone_f_code.json",
    "codebook\shards\zone_g_health.json",
    "codebook\shards\zone_h_legacy.json",
    "docs\final\master_codebook_dual_track.multidomain_1000.json",
    "docs\final\openapi_token_compression_stub_v1.yaml",
    "scripts\compression_token_api_v2_stub.py",
    "scripts\Serve-CompressionV2Explorer.ps1",
    "scripts\Start-CompressionV2ExplorerDemo.ps1",
    "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\compression_v2_explorer.html",
    "docs\final\schemas\mkm_user_context_v1.schema.json",
    "data\personalization\mkm_user_context_v1.sample.json",
    "docs\final\COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md",
    "scripts\bench_l1_api_load.py",
    "docs\final\artifacts\bench_l1_api_load_latest.json",
    "scripts\run_l1_inverse_decoder_spike_test.py",
    "scripts\l1_side_channel_wire_codec.py",
    "scripts\run_l1_permutation_channel_integrated_spike.py",
    "docs\final\artifacts\l1_inverse_decoder_spike_test_summary_latest.json",
    "docs\final\artifacts\l1_permutation_channel_integrated_spike_latest.json",
    "scripts\report_trackb_quaternion_two_stage_gate.py",
    "docs\final\artifacts\trackb_quaternion_order_experiment_v1.json",
    "docs\final\artifacts\trackb_quaternion_order_stress_v1.json",
    "docs\final\artifacts\trackb_quaternion_generalization_v1.json",
    "docs\final\artifacts\trackb_quaternion_two_stage_gate_v2.json",
    "scripts\experimental\codebook_runtime_pack\build_report_schema_v2_quality_alert.py",
    "scripts\experimental\codebook_runtime_pack\build_report_schema_v2_label_kpi.py",
    "codebook\policies\slack_fact_safe_mention_routing_v1.json"
)

$missing = @()
foreach ($rel in $required) {
    $p = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $p)) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host "FAIL: missing paths (see P0_COMMERCIALIZATION_TRACKER.md '증거 경로'):" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "OK: P0/CONSTITUTION gate paths present ($($required.Count) checked)."

$optionalQualityArtifacts = @(
    "docs\final\artifacts\report_schema_v2_quality_alert_latest.json",
    "docs\final\artifacts\report_schema_v2_label_kpi_latest.json",
    "docs\final\artifacts\report_schema_v2_latest.json"
)
$missingOptional = @()
foreach ($rel in $optionalQualityArtifacts) {
    $p = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $p)) {
        $missingOptional += $rel
    }
}
if ($missingOptional.Count -gt 0) {
    Write-Host "WARN: optional report_schema_v2 artifacts missing (run waiting_queue_monthly_check or build_report_schema_v2_* scripts):" -ForegroundColor Yellow
    $missingOptional | ForEach-Object { Write-Host "  $_" }
}

exit 0
