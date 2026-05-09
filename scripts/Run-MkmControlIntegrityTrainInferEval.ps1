#Requires -Version 5.1
<#
.SYNOPSIS
  One-click chain for MKM Control-Integrity:
  prep -> (optional train) -> inference -> evaluation

.EXAMPLE
  # Fast smoke without model load (oracle predictions)
  .\scripts\Run-MkmControlIntegrityTrainInferEval.ps1 -OracleInference

.EXAMPLE
  # Model inference on test split with fallback train dry-run
  .\scripts\Run-MkmControlIntegrityTrainInferEval.ps1 -TrainDryRun -InferenceSplit test
#>
param(
  [switch]$UseGoldenSet = $true,
  [switch]$SkipPrep = $false,
  [switch]$TrainDryRun = $true,
  [switch]$SkipTrainDryRun = $false,
  [ValidateSet('fallback','unsloth')]
  [string]$Backend = 'fallback',
  [ValidateSet('tiny-smoke','qwen-safe','gemma3-safe','qwen3-safe')]
  [string]$Profile = 'tiny-smoke',
  [ValidateSet('custom','a_qwen25_base','b_gemma3_upgrade','c_qwen3_research')]
  [string]$ModelProfile = 'custom',
  [ValidateSet('validation','test','locked_eval')]
  [string]$InferenceSplit = 'test',
  [string]$ModelName = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
  [string]$AdapterPath = '',
  [switch]$OracleInference,
  [int]$InferenceLimit = 0
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if ($ModelProfile -ne 'custom') {
  switch ($ModelProfile) {
    'a_qwen25_base' {
      $Backend = 'fallback'
      $Profile = 'qwen-safe'
      $ModelName = 'Qwen/Qwen2.5-7B-Instruct'
    }
    'b_gemma3_upgrade' {
      $Backend = 'fallback'
      $Profile = 'gemma3-safe'
      $ModelName = 'google/gemma-3-4b-it'
    }
    'c_qwen3_research' {
      $Backend = 'fallback'
      $Profile = 'qwen3-safe'
      $ModelName = 'Qwen/Qwen3-8B'
    }
  }
}

$ssotProfilesPath = Join-Path (Split-Path $PSScriptRoot -Parent) "docs/final/artifacts/mkm_control_integrity_lora_model_profiles_v1.json"
$ssotKeyByProfile = @{
  'tiny-smoke' = 'tiny_smoke'
  'qwen-safe' = 'qwen_safe'
  'gemma3-safe' = 'gemma3_safe'
  'qwen3-safe' = 'qwen3_safe'
}
if (Test-Path -LiteralPath $ssotProfilesPath) {
  $pk = $ssotKeyByProfile[$Profile]
  if ($pk) {
    try {
      $ssotDoc = Get-Content -Raw -LiteralPath $ssotProfilesPath | ConvertFrom-Json
      $profObj = $ssotDoc.profiles.$pk
      if ($profObj -and $profObj.model_id) {
        $ModelName = [string]$profObj.model_id
      }
    } catch {
      Write-Warning "SSOT overlay skipped: $($_.Exception.Message)"
    }
  }
}

if ($UseGoldenSet -and -not $SkipPrep) {
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/Invoke-LoraTrainLocalPrep.ps1" -UseControlIntegrityGoldenSet
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($TrainDryRun -and -not $SkipTrainDryRun) {
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/Run-MkmProphecyLoraTraining.ps1" -Backend $Backend -Profile $Profile -DatasetPath "data/training/mkm_control_integrity_lora_splits_v1/train.jsonl" -MaxSteps 1 -DryRun
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$splitIn = "data/training/mkm_control_integrity_lora_splits_v1/$InferenceSplit.jsonl"
$suffix = if ($ModelProfile -eq 'custom') { "custom" } else { $ModelProfile }
$predOut = "reports/mkm_control_integrity_predictions_${InferenceSplit}_${suffix}_latest.jsonl"
$evalOut = "reports/mkm_control_integrity_lora_eval_${InferenceSplit}_${suffix}_latest.json"

$inferArgs = @(
  "scripts/run_mkm_control_integrity_inference_batch_v1.py",
  "--in", $splitIn,
  "--out", $predOut,
  "--model-name", $ModelName
)

if ($AdapterPath) {
  $inferArgs += @("--adapter-path", $AdapterPath)
}
if ($OracleInference) {
  $inferArgs += "--oracle"
} else {
  $inferArgs += "--emit-timing"
}

if ($InferenceLimit -gt 0) {
  $inferArgs += @("--limit", "$InferenceLimit")
}

if (Test-Path -LiteralPath $ssotProfilesPath) {
  $inferArgs += @("--ssot-profiles-json", $ssotProfilesPath)
  $pkInfer = $ssotKeyByProfile[$Profile]
  if ($pkInfer) {
    $inferArgs += @("--ssot-profile-key", $pkInfer)
  }
}

py @inferArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$evalArgs = @(
  "scripts/evaluate_mkm_control_integrity_lora_predictions_v1.py",
  "--golden", "scripts/data/mkm_control_integrity_golden_set_v1_1000.jsonl",
  "--predictions", $predOut,
  "--splits", $InferenceSplit,
  "--report-out", $evalOut
)
if ($InferenceLimit -gt 0) {
  $evalArgs += "--allow-missing-predictions"
}
py @evalArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: profile=$ModelProfile split=$InferenceSplit oracle=$OracleInference report=$evalOut" -ForegroundColor Green
