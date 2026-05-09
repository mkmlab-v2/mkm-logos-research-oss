<#
.SYNOPSIS
  Run MKM prophecy LoRA training with Windows-safe defaults.

.DESCRIPTION
  Default backend is the Windows fallback trainer (Transformers + PEFT).
  Use -Backend unsloth only when your environment is known stable.
#>
param(
  [ValidateSet('fallback','unsloth')]
  [string]$Backend = 'fallback',
  [ValidateSet('tiny-smoke','qwen-safe','gemma3-safe','qwen3-safe')]
  [string]$Profile = 'tiny-smoke',
  [string]$DatasetPath = 'data/training/macro_prophecy_dataset_v1.jsonl',
  [int]$MaxSteps = 10,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = 'C:\workspace'
Set-Location -LiteralPath $root

$dataset = $DatasetPath
if (-not (Test-Path -LiteralPath $dataset)) {
  Write-Host "dataset not found: $dataset" -ForegroundColor Red
  exit 1
}

$profileJsonPath = Join-Path $root 'docs/final/artifacts/mkm_control_integrity_lora_model_profiles_v1.json'
$profileKeyMap = @{
  'tiny-smoke'  = 'tiny_smoke'
  'qwen-safe'   = 'qwen_safe'
  'gemma3-safe' = 'gemma3_safe'
  'qwen3-safe'  = 'qwen3_safe'
}

if ($Backend -eq 'fallback') {
  $runner = 'scripts/train_mkm_prophecy_lora_windows_fallback_v1.py'
  if ($Profile -eq 'tiny-smoke') {
    $model = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'
    $seq = 512
    $batch = 1
    $accum = 2
    $out = 'models/adapters/macro_prophecy_lora_windows_fallback_tinyllama_v1'
  } elseif ($Profile -eq 'qwen-safe') {
    $model = 'Qwen/Qwen2.5-7B-Instruct'
    $seq = 768
    $batch = 1
    $accum = 2
    $out = 'models/adapters/macro_prophecy_lora_windows_fallback_qwen_v1'
  } elseif ($Profile -eq 'gemma3-safe') {
    $model = 'google/gemma-3-4b-it'
    $seq = 768
    $batch = 1
    $accum = 2
    $out = 'models/adapters/macro_prophecy_lora_windows_fallback_gemma3_v1'
  } else {
    $model = 'Qwen/Qwen3-8B'
    $seq = 1024
    $batch = 1
    $accum = 2
    $out = 'models/adapters/macro_prophecy_lora_windows_fallback_qwen3_v1'
  }

  $loraR = 16
  $loraAlpha = 16
  $loraDropout = 0.05
  $lr = 0.0002

  if (Test-Path -LiteralPath $profileJsonPath) {
    try {
      $pj = Get-Content -Raw -LiteralPath $profileJsonPath | ConvertFrom-Json
      $pk = $profileKeyMap[$Profile]
      $prop = $pj.profiles.psobject.Properties[$pk]
      if ($prop) {
        $pr = $prop.Value
        if ($pr.model_id) { $model = [string]$pr.model_id }
        if ($null -ne $pr.max_seq_length) { $seq = [int]$pr.max_seq_length }
        if ($null -ne $pr.batch_size) { $batch = [int]$pr.batch_size }
        if ($null -ne $pr.grad_accum) { $accum = [int]$pr.grad_accum }
        if ($null -ne $pr.lora_r) { $loraR = [int]$pr.lora_r }
        if ($null -ne $pr.lora_alpha) { $loraAlpha = [int]$pr.lora_alpha }
        if ($null -ne $pr.lora_dropout) { $loraDropout = [double]$pr.lora_dropout }
        if ($null -ne $pr.learning_rate) { $lr = [double]$pr.learning_rate }
        Write-Host "[MKM-LORA] profile_ssot=$profileJsonPath key=$pk" -ForegroundColor DarkGray
      }
    } catch {
      Write-Host "[MKM-LORA] WARN: profile SSOT parse failed: $_" -ForegroundColor Yellow
    }
  }

  $args = @(
    $runner,
    '--dataset-path', $dataset,
    '--model-name', $model,
    '--max-seq-length', "$seq",
    '--max-steps', "$MaxSteps",
    '--batch-size', "$batch",
    '--grad-accum', "$accum",
    '--learning-rate', "$lr",
    '--lora-r', "$loraR",
    '--lora-alpha', "$loraAlpha",
    '--lora-dropout', "$loraDropout",
    '--output-dir', $out
  )
  if ($DryRun) { $args += '--dry-run' }

  Write-Host "[MKM-LORA] backend=fallback profile=$Profile model=$model steps=$MaxSteps dry_run=$DryRun"
  & py @args
  exit $LASTEXITCODE
}

# unsloth backend
$runner = 'scripts/train_mkm_prophecy_lora_unsloth.py'
if ($Profile -eq 'tiny-smoke') {
  $model = 'unsloth/Qwen2.5-7B-Instruct-bnb-4bit'
  $seq = 1024
  $batch = 1
  $out = 'models/adapters/macro_prophecy_lora_unsloth_v1'
} elseif ($Profile -eq 'qwen-safe') {
  $model = 'unsloth/Qwen2.5-7B-Instruct-bnb-4bit'
  $seq = 2048
  $batch = 1
  $out = 'models/adapters/macro_prophecy_lora_unsloth_v1'
} elseif ($Profile -eq 'qwen3-safe') {
  $model = 'Qwen/Qwen3-8B'
  $seq = 2048
  $batch = 1
  $out = 'models/adapters/macro_prophecy_lora_unsloth_qwen3_v1'
} else {
  Write-Host "Profile $Profile is not supported on unsloth backend. Use -Backend fallback for gemma3-safe." -ForegroundColor Red
  exit 1
}

$lr = 0.0002
$loraR = 16
$loraAlpha = 16
$loraDropout = 0
$accum = 4
$dataProc = 1

if (Test-Path -LiteralPath $profileJsonPath) {
  try {
    $pj = Get-Content -Raw -LiteralPath $profileJsonPath | ConvertFrom-Json
    $pk = $profileKeyMap[$Profile]
    $prop = $pj.profiles.psobject.Properties[$pk]
    if ($prop) {
      $pr = $prop.Value
      if ($pr.unsloth_model_id) { $model = [string]$pr.unsloth_model_id }
      if ($null -ne $pr.max_seq_length) { $seq = [int]$pr.max_seq_length }
      if ($null -ne $pr.batch_size) { $batch = [int]$pr.batch_size }
      if ($null -ne $pr.grad_accum) { $accum = [int]$pr.grad_accum }
      if ($null -ne $pr.lora_r) { $loraR = [int]$pr.lora_r }
      if ($null -ne $pr.lora_alpha) { $loraAlpha = [int]$pr.lora_alpha }
      if ($null -ne $pr.lora_dropout) { $loraDropout = [double]$pr.lora_dropout }
      if ($null -ne $pr.learning_rate) { $lr = [double]$pr.learning_rate }
      Write-Host "[MKM-LORA] profile_ssot(unsloth)=$profileJsonPath key=$pk" -ForegroundColor DarkGray
    }
  } catch {
    Write-Host "[MKM-LORA] WARN: profile SSOT parse failed (unsloth): $_" -ForegroundColor Yellow
  }
}

$args = @(
  $runner,
  '--dataset-path', $dataset,
  '--model-name', $model,
  '--max-seq-length', "$seq",
  '--max-steps', "$MaxSteps",
  '--batch-size', "$batch",
  '--learning-rate', "$lr",
  '--grad-accum', "$accum",
  '--lora-r', "$loraR",
  '--lora-alpha', "$loraAlpha",
  '--lora-dropout', "$loraDropout",
  '--dataset-num-proc', "$dataProc",
  '--output-dir', $out
)
if ($DryRun) { $args += '--dry-run' }

Write-Host "[MKM-LORA] backend=unsloth profile=$Profile model=$model seq=$seq steps=$MaxSteps dry_run=$DryRun"
& py @args
exit $LASTEXITCODE
