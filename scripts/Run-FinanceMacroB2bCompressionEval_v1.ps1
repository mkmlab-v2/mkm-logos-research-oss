<#
.SYNOPSIS
  Finance/macro Track C B2B compression eval: build input -> multilens performance report (experimental C/high).

.PARAMETER SkipBuildEvalInput
  Skip build_finance_macro_b2b_compression_eval_input_v1.py (use existing eval input JSON).

.PARAMETER DryRun
  Print planned py commands only; do not execute.
#>
param(
    [switch]$SkipBuildEvalInput,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Root

$buildArgs = @("scripts\build_finance_macro_b2b_compression_eval_input_v1.py")
$reportArgs = @(
    "scripts\report_multilens_performance_eval.py",
    "--input", "docs/final/artifacts/finance_macro_b2b_compression_eval_input_v1.json",
    "--output", "docs/final/artifacts/finance_macro_b2b_compression_active_report_v1.json",
    "--mode", "experimental",
    "--strategy", "C",
    "--intensity", "high"
)

function Invoke-PyStep {
    param([string]$Name, [string[]]$PyArgs)
    Write-Host "==> $Name"
    $cmd = "py " + ($PyArgs -join " ")
    Write-Host $cmd
    if (-not $DryRun) {
        & py @PyArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Step failed ($Name): exit code $LASTEXITCODE"
        }
    }
}

if (-not $SkipBuildEvalInput) {
    Invoke-PyStep "build_finance_macro_b2b_compression_eval_input_v1" $buildArgs
}
Invoke-PyStep "report_multilens_performance_eval" $reportArgs

if ($DryRun) {
    Write-Host "OK: DryRun complete (no commands executed)."
} else {
    Write-Host "OK: Finance macro B2B compression eval completed."
}
