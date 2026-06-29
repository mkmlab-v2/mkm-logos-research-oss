#Requires -Version 5.1
<#
.SYNOPSIS
  B-track predictability harness — gate + Brier/ECE + drift log (research_only).

.DESCRIPTION
  No Track A / live trading. Default registry: docs/final/artifacts/general_prophecy_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$RegistryPath = "",
    [switch]$DryRun,
    [switch]$SkipAppend
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

$args = @("scripts/run_btrack_predictability_harness_v1.py")
if ($RegistryPath) {
    $args += @("-i", $RegistryPath)
}
if ($DryRun) { $args += "--dry-run" }
if ($SkipAppend) { $args += "--skip-append" }

& $py @args
exit $LASTEXITCODE
