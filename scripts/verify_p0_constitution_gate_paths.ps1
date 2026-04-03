param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$required = @(
    "docs\final\CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs\final\P0_COMMERCIALIZATION_TRACKER.md",
    "docs\final\COMPRESSION_SLA_POLICY_V1.md",
    "docs\final\COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs\NotebookLM_sources_manifest.md",
    ".cursorrules",
    "AGENTS.md",
    "CLAUDE.md",
    "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1",
    "scripts\run_waiting_queue_monthly_check.ps1",
    "projects\bitcoin-trading\ops\v2\tasks\run_prophecy_alignment_pytest.ps1"
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
exit 0
