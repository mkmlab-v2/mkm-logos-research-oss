<#
.SYNOPSIS
  Fast smoke: rebuild general_compression_eval_input, assert non-empty cases, optionally validate evidence bundle.

.PARAMETER SkipValidate
  Skip validate_general_compression_bundle.py (use when evidence JSON/CSV not yet generated).
#>
param([switch] $SkipValidate)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> build_general_compression_eval_input"
py scripts/build_general_compression_eval_input.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> pytest build_general_compression_eval_input smoke"
py -m pytest tests/test_build_general_compression_eval_input_smoke_v1.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipValidate) {
    $need = @(
        "docs/final/artifacts/general_compression_ab_result_summary_v1.json",
        "docs/final/artifacts/general_compression_ab_result_timeseries_v1.csv",
        "docs/final/artifacts/general_compression_repro_command_v1.txt",
        "docs/final/artifacts/general_compression_kpi_gate_v2.json"
    )
    $missing = @()
    foreach ($rel in $need) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root $rel))) { $missing += $rel }
    }
    if ($missing.Count -gt 0) {
        Write-Host "WARN: Skip validate (missing:" ($missing -join ", ") ") — run Run-GeneralCompressionChain.ps1 once."
    }
    else {
        Write-Host "==> validate_general_compression_bundle"
        py scripts/validate_general_compression_bundle.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host "OK: General compression bundle smoke completed."
