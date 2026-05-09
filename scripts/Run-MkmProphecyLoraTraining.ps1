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
  [ValidateSet('tiny-smoke','qwen-safe')]
  [string]$Profile = 'tiny-smoke',
  [int]$MaxSteps = 10,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = 'C:\workspace'
Set-Location -LiteralPath $root

$dataset = 'data/training/macro_prophecy_dataset_v1.jsonl'

if ($Backend -eq 'fallback') {
  $runner = 'scripts/train_mkm_prophecy_lora_windows_fallback_v1.py'
  if ($Profile -eq 'tiny-smoke') {
    $model = 'TinyLlama/TinyLlama-1.1B-Chat-v1.0'
    $seq = 512
    $batch = 1
    $accum = 2
    $out = 'models/adapters/macro_prophecy_lora_windows_fallback_tinyllama_v1'
  } else {
    $model = 'Qwen/Qwen2.5-7B-Instruct'
    $seq = 768
    $batch = 1
    $accum = 2
    $out = 'models/adapters/macro_prophecy_lora_windows_fallback_qwen_v1'
  }

  $args = @(
    $runner,
    '--dataset-path', $dataset,
    '--model-name', $model,
    '--max-seq-length', "$seq",
    '--max-steps', "$MaxSteps",
    '--batch-size', "$batch",
    '--grad-accum', "$accum",
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
} else {
  $model = 'unsloth/Qwen2.5-7B-Instruct-bnb-4bit'
  $seq = 2048
  $batch = 1
  $out = 'models/adapters/macro_prophecy_lora_unsloth_v1'
}

$args = @(
  $runner,
  '--dataset-path', $dataset,
  '--model-name', $model,
  '--max-seq-length', "$seq",
  '--max-steps', "$MaxSteps",
  '--batch-size', "$batch",
  '--dataset-num-proc', '1',
  '--output-dir', $out
)
if ($DryRun) { $args += '--dry-run' }

Write-Host "[MKM-LORA] backend=unsloth profile=$Profile model=$model steps=$MaxSteps dry_run=$DryRun"
& py @args
exit $LASTEXITCODE
