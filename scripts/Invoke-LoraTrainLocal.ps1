#Requires -Version 5.1
<#
.SYNOPSIS
  Run macro_prophecy LoRA training on this Windows machine using the cu128 venv (RTX 50 / sm_120).
  Extra args are passed to scripts/train_mkm_prophecy_lora_unsloth.py
.EXAMPLE
  .\scripts\Invoke-LoraTrainLocal.ps1 --max-steps 10 --batch-size 1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv_lora_local128\Scripts\python.exe"
$train = Join-Path $root "scripts\train_mkm_prophecy_lora_unsloth.py"
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "Missing $py — create venv with PyTorch cu128 + unsloth (see docs/final/CURRENT_OPS_SNAPSHOT.md)." -ForegroundColor Red
    exit 1
}
& $py $train @args
exit $LASTEXITCODE
