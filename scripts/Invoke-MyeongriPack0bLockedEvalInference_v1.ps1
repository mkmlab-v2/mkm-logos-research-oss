#Requires -Version 5.1
<#
.SYNOPSIS
  Run Pack 0-B locked_eval alignment inference (GPU) against a trained adapter.

.DESCRIPTION
  Thin wrapper over scripts/run_myeongri_deterministic_lora_inference_eval_v1.py.
  Defaults match bulk layout when present; override paths if your golden lives elsewhere.

.PARAMETER GoldenLockedEvalJsonl
  Golden JSONL containing locked_eval rows (default: repo bulk path).

.PARAMETER AdapterPath
  PEFT adapter directory (default: last known train_default smoke path).

.PARAMETER Limit
  Optional max rows (0 = all).

.EXAMPLE
  pwsh -File scripts/Invoke-MyeongriPack0bLockedEvalInference_v1.ps1 -Limit 10
#>
param(
    [string] $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string] $GoldenLockedEvalJsonl = "",
    [string] $AdapterPath = "",
    [int] $Limit = 0
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if (-not $GoldenLockedEvalJsonl) {
    $GoldenLockedEvalJsonl = Join-Path $WorkspaceRoot "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
}
if (-not $AdapterPath) {
    $AdapterPath = Join-Path $WorkspaceRoot "storage/adapters/myeongri_deterministic_lora_v0/run_train_default_20260513_s20"
}

if (-not (Test-Path -LiteralPath $GoldenLockedEvalJsonl)) {
    Write-Error "Golden JSONL not found: $GoldenLockedEvalJsonl — copy bulk data or pass -GoldenLockedEvalJsonl."
    exit 1
}
if (-not (Test-Path -LiteralPath $AdapterPath)) {
    Write-Error "Adapter directory not found: $AdapterPath — train first or pass -AdapterPath."
    exit 1
}

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) {
    $py = "python"
}

$argsList = @(
    "scripts/run_myeongri_deterministic_lora_inference_eval_v1.py",
    "--golden-jsonl", $GoldenLockedEvalJsonl,
    "--adapter-path", $AdapterPath,
    "--profile-key", "train_default",
    "--split", "locked_eval",
    "--emit-timing"
)
if ($Limit -gt 0) {
    $argsList += @("--limit", "$Limit")
}

& $py @argsList
exit $LASTEXITCODE
