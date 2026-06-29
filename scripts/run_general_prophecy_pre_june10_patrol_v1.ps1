#Requires -Version 5.1
<#
.SYNOPSIS
  general_prophecy patrol before 2026-06-10: BLS preflight, Logos data, June observation, holdout, 31k shadow (optional).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Include31kShadow,
    [switch]$SkipHoldout
)

$ErrorActionPreference = "Stop"
Push-Location $WorkspaceRoot
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 `
        -WorkspaceRoot $WorkspaceRoot -PatrolOnly

    & py scripts/check_general_prophecy_logos_june_resolve_preflight_v1.py

    & py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/check_logos_gp_resolve_preflight_v1.py
    & py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/run_logos_gp_resolve_preview_v1.py

    if (-not $SkipHoldout) {
        & py scripts/report_general_prophecy_explainability_quality_v1.py
        & py scripts/build_general_prophecy_explainability_holdout_report_v1.py
        & py scripts/check_general_prophecy_explainability_holdout_gate_v1.py --profile research
    }

    if ($Include31kShadow) {
        & py scripts/run_btrack_31k41k_prophecy_shadow_chain_v1.py --daily-fast
    }

    Write-Host "pre_june10_patrol: done" -ForegroundColor Green
    exit 0
}
finally {
    Pop-Location
}
