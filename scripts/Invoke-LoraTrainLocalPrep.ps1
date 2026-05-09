#Requires -Version 5.1
<#
.SYNOPSIS
  Local prep for macro_prophecy LoRA: export JSONL + dry-run (no GPU training).
  Remote GPU training: copy repo to VPS and run scripts/lora_train_remote_gpu_bootstrap.sh (Linux).
#>
param(
  [switch]$UseControlIntegrityGoldenSet
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if ($UseControlIntegrityGoldenSet) {
  py scripts/generate_mkm_control_integrity_golden_set_1000_v1.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  py scripts/validate_mkm_control_integrity_golden_set_v1.py --in scripts/data/mkm_control_integrity_golden_set_v1_1000.jsonl --report-out reports/mkm_control_integrity_golden_set_v1_validation_1000_latest.json
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  py scripts/convert_mkm_control_integrity_to_lora_v1.py --in scripts/data/mkm_control_integrity_golden_set_v1_1000.jsonl --out data/training/mkm_control_integrity_lora_1000.jsonl
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  py scripts/split_mkm_control_integrity_lora_by_split_v1.py --in data/training/mkm_control_integrity_lora_1000.jsonl --out-dir data/training/mkm_control_integrity_lora_splits_v1
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
  py scripts/export_general_prophecy_to_jsonl.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($UseControlIntegrityGoldenSet) {
  py scripts/train_mkm_prophecy_lora_unsloth.py --dataset-path data/training/mkm_control_integrity_lora_splits_v1/train.jsonl --dry-run
} else {
  py scripts/train_mkm_prophecy_lora_unsloth.py --dry-run
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($UseControlIntegrityGoldenSet) {
  Write-Host "OK: Golden Set v1 1000 -> LoRA split(train) + dry-run completed." -ForegroundColor Green
  Write-Host "Train example: .\scripts\Run-MkmProphecyLoraTraining.ps1 -Backend fallback -Profile tiny-smoke -DatasetPath data/training/mkm_control_integrity_lora_splits_v1/train.jsonl -MaxSteps 10"
} else {
  Write-Host "OK: dataset + dry-run. Remote: bash scripts/lora_train_remote_gpu_bootstrap.sh --max-steps 10 --batch-size 1" -ForegroundColor Green
}
