#Requires -Version 5.1
<#
.SYNOPSIS
  W4 B2B compression bench prep — MASK HYPO audit + launch checklist refresh + pack build.

.DESCRIPTION
  Lane A B2B · research_only guardrails · external launch stays BLOCKED_BY_READINESS.
  Does not unlock SEND or Track A ACTIVE swap.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-CompressionB2bWeek4Routine_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipLaunchChecklist,
    [switch]$SkipEnterpriseReadiness
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$steps = [ordered]@{}

Write-Host "=== W4: MASK HYPO passive cross-audit ===" -ForegroundColor Cyan
& py scripts\run_compression_mask_hypo_passive_cross_audit_v1.py
$steps.hypo_cross_audit_exit = [int]$LASTEXITCODE
if ($steps.hypo_cross_audit_exit -ne 0) {
    Write-Error "MASK HYPO passive cross-audit failed (exit $($steps.hypo_cross_audit_exit))"
}

if (-not $SkipLaunchChecklist) {
    Write-Host "=== W4: launch checklist refresh ===" -ForegroundColor Cyan
    & py scripts\build_a_codeai_public_benchmark_launch_checklist_v1.py
    $steps.launch_checklist_exit = [int]$LASTEXITCODE
} else {
    $steps.launch_checklist_exit = 0
    $steps.launch_checklist_skipped = $true
}

Write-Host "=== W4: bench prep pack build ===" -ForegroundColor Cyan
& py scripts\build_compression_b2b_w4_bench_prep_pack_v1.py
$steps.w4_pack_exit = [int]$LASTEXITCODE
if ($steps.w4_pack_exit -ne 0) {
    Write-Error "W4 bench prep pack build failed (exit $($steps.w4_pack_exit))"
}

if (-not $SkipEnterpriseReadiness) {
    Write-Host "=== W4: enterprise summary readiness (non-gating) ===" -ForegroundColor Cyan
    & py scripts\check_compression_enterprise_summary_readiness_v1.py --stdout-only
    $steps.enterprise_readiness_exit = [int]$LASTEXITCODE
} else {
    $steps.enterprise_readiness_exit = 0
    $steps.enterprise_readiness_skipped = $true
}

$outJson = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_b2b_w4_bench_prep_pack_v1_latest.json"
Write-Host "=== W4 routine complete ===" -ForegroundColor Green
Write-Host "pack: $outJson"
Write-Host ($steps | ConvertTo-Json -Compress)
exit 0
