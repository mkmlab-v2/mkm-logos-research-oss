#Requires -Version 5.1
<#
.SYNOPSIS
  Serial Qwen 7B Control-Integrity holdout: test -> locked_eval -> aggregate -> promotion gate.
  Writes progress to reports/qwen_strict_chain_auto_log.txt (append).
  Default promotion gate: human sign-off profile (holdout-only, locked_eval>=0.68, weighted row_pass>=0.70). Use -StrictPromotionGate for ABC+0.85/0.80.
#>
param(
  [string]$AdapterPath = "models/adapters/macro_prophecy_lora_windows_fallback_qwen_v1",
  [string]$LogPath = "reports/qwen_strict_chain_auto_log.txt",
  # Off by default: use sign-off gate (auto GO when latest holdout meets agreed floors). Set for CI / strict regression.
  [switch]$StrictPromotionGate = $false
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root

function Write-Step([string]$msg) {
  $line = "$(Get-Date -Format o) $msg"
  Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8
  Write-Host $line
}

Write-Step "=== Qwen strict chain v1 START adapter=$AdapterPath ==="

$trainInfer = Join-Path $root "scripts\Run-MkmControlIntegrityTrainInferEval.ps1"

foreach ($split in @("test", "locked_eval")) {
  Write-Step "BEGIN split=$split"
  # Invoke in-process (no nested powershell.exe) so exit codes and logging stay coherent.
  & $trainInfer `
    -SkipPrep `
    -SkipTrainDryRun `
    -ModelProfile "a_qwen25_base" `
    -AdapterPath $AdapterPath `
    -InferenceSplit $split
  $ec = $LASTEXITCODE
  Write-Step "END split=$split exit=$ec"
  if ($ec -ne 0) {
    Write-Step "ABORT chain at split=$split"
    exit $ec
  }
}

Write-Step "BEGIN aggregate"
py (Join-Path $root "scripts\aggregate_mkm_control_integrity_eval_holdout_v1.py") @(
  "--inputs", "reports/mkm_control_integrity_lora_eval_validation_a_qwen25_base_latest.json,reports/mkm_control_integrity_lora_eval_test_a_qwen25_base_latest.json,reports/mkm_control_integrity_lora_eval_locked_eval_a_qwen25_base_latest.json",
  "--profile-label", "qwen25_7b_lora_300_strict",
  "--out", "reports/mkm_control_integrity_lora_eval_holdout_suite_qwen25_7b_lora_300_strict_latest.json"
)
if ($LASTEXITCODE -ne 0) {
  Write-Step "ABORT aggregate exit=$LASTEXITCODE"
  exit $LASTEXITCODE
}
Write-Step "END aggregate exit=0"

Write-Step "BEGIN promotion_gate"
if ($StrictPromotionGate) {
  Write-Step "promotion_gate mode=StrictPromotionGate (ABC comparison + 0.85/0.80 holdout floors)"
  py (Join-Path $root "scripts\check_mkm_control_integrity_promotion_gate_v1.py") @(
    "--min-row-pass-rate", "0.70",
    "--min-must-include-rate", "0.70",
    "--holdout-report", "reports/mkm_control_integrity_lora_eval_holdout_suite_qwen25_7b_lora_300_strict_latest.json",
    "--min-locked-eval-pass-rate", "0.85",
    "--min-holdout-row-pass-weighted", "0.80",
    "--report-out", "reports/mkm_control_integrity_promotion_gate_strict_latest.json"
  )
} else {
  Write-Step "promotion_gate mode=default_signoff (holdout-only, locked_eval>=0.68, weighted>=0.70)"
  py (Join-Path $root "scripts\check_mkm_control_integrity_promotion_gate_v1.py") @(
    "--holdout-only",
    "--holdout-report", "reports/mkm_control_integrity_lora_eval_holdout_suite_qwen25_7b_lora_300_strict_latest.json",
    "--min-locked-eval-pass-rate", "0.68",
    "--min-holdout-row-pass-weighted", "0.70"
  )
}
$ge = $LASTEXITCODE
Write-Step "END promotion_gate exit=$ge"
Write-Step "=== Qwen strict chain v1 DONE ==="
exit $ge
