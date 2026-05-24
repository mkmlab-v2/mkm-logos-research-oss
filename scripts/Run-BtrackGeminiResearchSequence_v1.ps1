#Requires -Version 5.1
<#
.SYNOPSIS
  Step 1 fair compare (30d) then Step 2 Gemini 180d OOS (long API run).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipOos180,
    [switch]$OosOnly,
    [switch]$SkipFairCompare
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot
$env:GOOGLE_GENAI_USE_VERTEXAI = "0"

if (-not $OosOnly -and -not $SkipFairCompare) {
    Write-Host "==> Step 1: fair compare (30d raw vs min_conf gated vs prod)" -ForegroundColor Cyan
    py scripts/run_btrack_gemini_fair_compare_chain_v1.py
    if ($LASTEXITCODE -ne 0) { throw "fair compare exit $LASTEXITCODE" }
}

if (-not $SkipOos180) {
    Write-Host "==> Step 2: Gemini per-date 180d OOS (cached API; may take ~1h)" -ForegroundColor Cyan
    py scripts/run_btrack_gemini_per_date_oos_180d_v1.py
    if ($LASTEXITCODE -ne 0) { throw "oos 180d exit $LASTEXITCODE" }
}

Write-Host "[OK] Gemini research sequence complete" -ForegroundColor Green
