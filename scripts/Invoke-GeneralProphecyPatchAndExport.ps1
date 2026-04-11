#Requires -Version 5.1
<#
.SYNOPSIS
  Apply a general_prophecy_registry_patch_v1 JSON, then export LoRA JSONL (Fact-Lock B rail).
.DESCRIPTION
  1) py scripts/apply_general_prophecy_registry_patches_v1.py --patch <file>
  2) py scripts/export_general_prophecy_to_jsonl.py  -> data/training/macro_prophecy_dataset_v1.jsonl

  Human gate: review the patch file (diff / schema) before running. This script does not call NotebookLM.

.PARAMETER Patch
  Path to patch JSON (schema general_prophecy_registry_patch_v1).

.PARAMETER DryRun
  Passes --dry-run to apply only (registry unchanged); skips export.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-GeneralProphecyPatchAndExport.ps1 -Patch patches\my_patch.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-GeneralProphecyPatchAndExport.ps1 -Patch patches\my_patch.json -DryRun
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Patch,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$p = Resolve-Path -LiteralPath $Patch -ErrorAction Stop

$applyArgs = @("scripts/apply_general_prophecy_registry_patches_v1.py", "--patch", $p.Path)
if ($DryRun) {
    $applyArgs += "--dry-run"
}

py @applyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($DryRun) {
    Write-Host "OK: apply --dry-run only (registry unchanged; export skipped)." -ForegroundColor Green
    exit 0
}

py scripts/export_general_prophecy_to_jsonl.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: registry patched + data/training/macro_prophecy_dataset_v1.jsonl refreshed. LoRA: Invoke-LoraTrainLocalPrep.ps1 or Invoke-LoraTrainLocal.ps1" -ForegroundColor Green
exit 0
