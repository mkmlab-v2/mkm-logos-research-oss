#Requires -Version 5.1
<#
.SYNOPSIS
  Run inference+eval for validation, test, locked_eval; merge into one holdout report.

.EXAMPLE
  # Oracle smoke (default): prep once, train dry-run once, three splits, merged holdout JSON
  .\scripts\Run-MkmControlIntegrityHoldoutEvalSuite.ps1 -ModelProfile a_qwen25_base

.EXAMPLE
  # Real model load (heavy): disable oracle
  .\scripts\Run-MkmControlIntegrityHoldoutEvalSuite.ps1 -ModelProfile a_qwen25_base -RealModelInference
#>
param(
  [ValidateSet('custom','a_qwen25_base','b_gemma3_upgrade','c_qwen3_research')]
  [string]$ModelProfile = 'a_qwen25_base',
  [switch]$RealModelInference,
  [switch]$SkipPrep = $false,
  [switch]$SkipTrainDryRun = $false
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$OracleInference = -not $RealModelInference

$suffix = if ($ModelProfile -eq 'custom') { "custom" } else { $ModelProfile }
$splits = @('validation','test','locked_eval')
$reports = @()

for ($i = 0; $i -lt $splits.Count; $i++) {
  $sp = $splits[$i]
  $useGolden = -not $SkipPrep -and ($i -eq 0)
  $trainDryThis = (-not $SkipTrainDryRun) -and ($i -eq 0)
  $invokeParams = @{
    ModelProfile = $ModelProfile
    InferenceSplit = $sp
    UseGoldenSet = $useGolden
    TrainDryRun = $trainDryThis
    OracleInference = $OracleInference
  }
  & "scripts/Run-MkmControlIntegrityTrainInferEval.ps1" @invokeParams
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  $reports += "reports/mkm_control_integrity_lora_eval_${sp}_${suffix}_latest.json"
}

$merged = "reports/mkm_control_integrity_lora_eval_holdout_suite_${suffix}_latest.json"
py scripts/aggregate_mkm_control_integrity_eval_holdout_v1.py --inputs ($reports -join ',') --profile-label $ModelProfile --out $merged
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: holdout suite report=$merged" -ForegroundColor Green
