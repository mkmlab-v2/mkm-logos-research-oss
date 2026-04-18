param(
    [string]$WorkspaceRoot = "C:\workspace"
)

# P0 path gate: every entry must exist in the workspace. Prune when files are not
# in this clone; re-add from main when those scripts return. (Track A metering
# multiline, kospi WF verify, etc. were removed 2026-04-18 for local pass.)

$ErrorActionPreference = "Stop"
$required = @(
    "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs\final\MKM12_PRISM_INDEX_REGISTRY_V1.json",
    "docs\final\P0_COMMERCIALIZATION_TRACKER.md",
    "docs\final\COMPRESSION_SLA_POLICY_V1.md",
    "docs\final\COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs\final\BENCH_L1_API_LOAD_VPS_RUNBOOK.md",
    "docs\NotebookLM_sources_manifest.md",
    "docs\final\NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md",
    "scripts\build_btrack_insight_bridge_inventory_v1.py",
    "scripts\build_btrack_insight_promotion_bridge_index_v1.py",
    "scripts\build_btrack_prophecy_score_insight_sidecar_stub_v1.py",
    "docs\final\schemas\btrack_prophecy_score_insight_sidecar_v1.schema.json",
    "docs\final\artifacts\btrack_prophecy_score_insight_sidecar_v1_latest.json",
    "scripts\eval_btrack_insight_sidecar_lens_hit_agreement_v1.py",
    "docs\final\artifacts\btrack_insight_sidecar_lens_hit_agreement_v1_latest.json",
    "scripts\Run-BtrackInsightSidecarChain.ps1",
    "scripts\register_btrack_insight_sidecar_chain_task.ps1",
    ".cursorrules",
    "AGENTS.md",
    "README.md",
    "projects\bitcoin-trading\AGENTS.md",
    "CLAUDE.md",
    "docs\final\LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md",
    "docs\final\NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md",
    "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1",
    "scripts\run_multilens_v2_bridge_policy_snapshot.py",
    "scripts\run_waiting_queue_monthly_check.ps1",
    "projects\bitcoin-trading\ops\windows-rehearsal\GENERAL_PROPHECY_MONTHLY_SCHEDULER_RUNBOOK_V1.md",
    "projects\bitcoin-trading\ops\windows-rehearsal\register_fused_quant_pixel_sop_strict_check_task.ps1",
    "projects\bitcoin-trading\ops\windows-rehearsal\register_fused_quant_pixel_sop_strict_check_task_clean.ps1",
    "scripts\eval_prophecy_hit_rate_v1.py",
    "scripts\fetch_kospi_yfinance_csv.py",
    "tests\test_load_kospi_yf_rows.py",
    "docs\final\GENERAL_PROPHECY_SCHEMA_V1.json",
    "scripts\generate_general_prophecy_v1.py",
    "scripts\build_general_prophecy_brief.py",
    "scripts\eval_general_prophecy_brier_score.py",
    "scripts\export_general_prophecy_to_jsonl.py",
    "scripts\apply_general_prophecy_registry_patches_v1.py",
    "scripts\Invoke-GeneralProphecyPatchAndExport.ps1",
    "scripts\Invoke-GeneralProphecyExportThenLora.ps1",
    "scripts\resolve_general_prophecy_question_v1.py",
    "tests\fixtures\general_prophecy_registry_sample_v1.json",
    "tests\fixtures\general_prophecy_registry_seed_5_v1.json",
    "tests\fixtures\general_prophecy_registry_brier_smoke_v1.json",
    "tests\fixtures\general_prophecy_registry_official_seed_v1.json",
    "tests\fixtures\general_prophecy_registry_macro_h2_2026_pack_v1.json",
    "tests\test_export_general_prophecy_to_jsonl.py",
    "tests\test_apply_general_prophecy_registry_patches_v1.py",
    "tests\fixtures\general_prophecy_registry_patch_sample_v1.json",
    "scripts\generate_btrack_hypothesis_prophecy_v1.py",
    "scripts\build_logos_wide_restoration.py",
    "scripts\build_btrack_prophecy_score_from_ohlcv.py",
    "scripts\run_daily_prophecy_eval_and_report.ps1",
    "scripts\report_btrack_notebooklm_jsonl_kpi.py",
    "projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1",
    "scripts\build_myeongri_sasang_codebook_spike_v1.py",
    "scripts\spike_4grid_myeongri_compression_v1.py",
    "scripts\Run-4GridMyeongriCompressionSpikeV1.ps1",
    "tests\test_spike_4grid_myeongri_compression_v1.py",
    "scripts\core\track_source_guard.py",
    "scripts\core\sovereign_jsonl.py",
    "scripts\spike_sovereign_token_saving.py",
    "scripts\spike_sovereign_vocab_efficiency.py",
    "tests\test_track_source_guard.py",
    "tests\test_sovereign_jsonl.py",
    "tests\test_spike_sovereign_token_saving_v1.py",
    "tests\test_sovereign_efficiency.py",
    "data\track_a_shadow\conversations_sample_v1.jsonl",
    "scripts\core\domain_router.py",
    "scripts\core\multilens_bridge_policy_env.py",
    "scripts\run_prophecy_restoration_spike.py",
    "tests\test_prophecy_restoration_spike.py",
    "docs\final\artifacts\prophecy_overlay_prior_threshold_recommended_latest.json",
    "docs\final\artifacts\prophecy_prior_threshold_sweep_summary_latest.json",
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
    "docs\final\schemas\mkm_compressed_payload_v1.schema.json",
    "scripts\dump_mcp_tool_inventory.py",
    "scripts\mkm_unified_mcp.py",
    "rag_server\mcp_server.py",
    "rag_server\cursor-mcp.env",
    "scripts\requirements-mkm-mcp.txt",
    "docs\final\artifacts\mkm_mcp_tool_audit_v1.json",
    "docs\final\artifacts\MKM_MCP_STDIO_POINTER_V1.json",
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
