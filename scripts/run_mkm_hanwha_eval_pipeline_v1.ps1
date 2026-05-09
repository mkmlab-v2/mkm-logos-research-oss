<#
.SYNOPSIS
  One-click pipeline for MKM Hanwha evaluation records.

.DESCRIPTION
  1) Auto-fill actual_next_day_return_pct and actual_3d_return_pct from close_t
  2) Evaluate score with calibration and gating
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$CsvPath = "reports/mkm_hanwha_prediction_eval_records_v1.csv",
    [string]$OutputJson = "reports/mkm_hanwha_prediction_eval_score_latest.json",
    [ValidateSet("auto", "temperature", "isotonic", "none")]
    [string]$CalibrationMode = "auto",
    [int]$MinRowsForGrade = 20,
    [int]$HoldoutLastN = 5,
    [switch]$OverwriteExistingActuals
)

$ErrorActionPreference = "Stop"

$fillScript = Join-Path $WorkspaceRoot "scripts\update_mkm_hanwha_eval_actuals_v1.py"
$evalScript = Join-Path $WorkspaceRoot "scripts\evaluate_mkm_hanwha_prediction_eval_v1.py"

if (-not (Test-Path -LiteralPath $fillScript)) { throw "Missing script: $fillScript" }
if (-not (Test-Path -LiteralPath $evalScript)) { throw "Missing script: $evalScript" }

Set-Location -LiteralPath $WorkspaceRoot

Write-Host "[1/2] Autofill actual returns..." -ForegroundColor Cyan
$fillArgs = @($fillScript, "--csv-path", $CsvPath)
if ($OverwriteExistingActuals) { $fillArgs += "--overwrite-existing" }
& py @fillArgs
if ($LASTEXITCODE -ne 0) { throw "Auto-fill failed with exit $LASTEXITCODE" }

Write-Host "[2/2] Evaluate score..." -ForegroundColor Cyan
& py $evalScript `
    --input-csv $CsvPath `
    --output-json $OutputJson `
    --calibration-mode $CalibrationMode `
    --min-rows-for-grade $MinRowsForGrade `
    --holdout-last-n $HoldoutLastN
if ($LASTEXITCODE -ne 0) { throw "Evaluation failed with exit $LASTEXITCODE" }

Write-Host "DONE: $OutputJson" -ForegroundColor Green
