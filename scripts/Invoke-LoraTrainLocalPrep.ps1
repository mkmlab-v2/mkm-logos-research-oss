#Requires -Version 5.1
<#
.SYNOPSIS
  Local prep for macro_prophecy LoRA: export JSONL + dry-run (no GPU training).
  Remote GPU training: copy repo to VPS and run scripts/lora_train_remote_gpu_bootstrap.sh (Linux).
#>
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

py scripts/export_general_prophecy_to_jsonl.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/train_mkm_prophecy_lora_unsloth.py --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: dataset + dry-run. Remote: bash scripts/lora_train_remote_gpu_bootstrap.sh --max-steps 10 --batch-size 1" -ForegroundColor Green
