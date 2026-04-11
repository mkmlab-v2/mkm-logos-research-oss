#Requires -Version 5.1
<#
.SYNOPSIS
  Export macro_prophecy_dataset_v1.jsonl from registry, then run local LoRA training (cu128 venv).
.DESCRIPTION
  1) py scripts/export_general_prophecy_to_jsonl.py
  2) scripts/Invoke-LoraTrainLocal.ps1 (pass-through args to train_mkm_prophecy_lora_unsloth.py)

  Use after registry is already updated (generate/merge/patch). For patch+export only, use Invoke-GeneralProphecyPatchAndExport.ps1.
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-GeneralProphecyExportThenLora.ps1 --max-steps 10 --batch-size 1
#>
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

py scripts/export_general_prophecy_to_jsonl.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$lora = Join-Path $PSScriptRoot "Invoke-LoraTrainLocal.ps1"
& $lora @args
exit $LASTEXITCODE
