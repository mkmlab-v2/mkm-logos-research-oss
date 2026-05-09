#Requires -Version 5.1
<#
.SYNOPSIS
  Run MKM Control-Integrity A/B/C model profile benchmark (inference + eval)
  and build consolidated comparison artifact.

.DESCRIPTION
  Default mode uses oracle inference for fast pipeline verification.
  Pass -RealModelInference to load base models (heavy).

.EXAMPLE
  .\scripts\Run-MkmControlIntegrityModelProfileABC.ps1 -RunHoldoutSuite -HoldoutModelProfile a_qwen25_base
#>
param(
  [ValidateSet('validation','test','locked_eval')]
  [string]$InferenceSplit = 'test',
  [switch]$RealModelInference,
  [switch]$SkipPrep = $false,
  [switch]$SkipTrainDryRun = $false,
  [switch]$RunHoldoutSuite = $false,
  [ValidateSet('custom','a_qwen25_base','b_gemma3_upgrade','c_qwen3_research')]
  [string]$HoldoutModelProfile = 'a_qwen25_base'
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$OracleInference = -not $RealModelInference

$profiles = @('a_qwen25_base','b_gemma3_upgrade','c_qwen3_research')

for ($i = 0; $i -lt $profiles.Count; $i++) {
  $profile = $profiles[$i]
  $useGolden = $true
  if ($SkipPrep -or $i -gt 0) {
    $useGolden = $false
  }

  $trainDryThis = (-not $SkipTrainDryRun) -and ($i -eq 0)

  $invokeParams = @{
    ModelProfile = $profile
    InferenceSplit = $InferenceSplit
    UseGoldenSet = $useGolden
    TrainDryRun = $trainDryThis
    OracleInference = $OracleInference
  }

  & "scripts/Run-MkmControlIntegrityTrainInferEval.ps1" @invokeParams
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/build_mkm_control_integrity_model_profile_abc_comparison_v1.py --out docs/final/artifacts/model_profile_abc_comparison_latest.json
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: ABC comparison generated at docs/final/artifacts/model_profile_abc_comparison_latest.json" -ForegroundColor Green

if ($RunHoldoutSuite) {
  $holdoutParams = @{
    ModelProfile = $HoldoutModelProfile
    SkipPrep = $true
    SkipTrainDryRun = $true
  }
  if ($RealModelInference) {
    $holdoutParams['RealModelInference'] = $true
  }
  & "scripts/Run-MkmControlIntegrityHoldoutEvalSuite.ps1" @holdoutParams
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
