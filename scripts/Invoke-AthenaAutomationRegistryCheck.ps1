#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot check for Athena automation scope (Windows Task Scheduler vs automation_registry.json).

.DESCRIPTION
  Wraps projects/bitcoin-trading/ops/windows-rehearsal/reconcile_automation_registry.ps1.
  Extended-deck tasks may be marked optional in the registry; missing optional tasks do not fail reconcile.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-AthenaAutomationRegistryCheck.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-AthenaAutomationRegistryCheck.ps1 -Enforce
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Enforce,
    [switch]$ShowJson,
    [switch]$IgnoreExecutionHealth
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    throw "WorkspaceRoot not found: $WorkspaceRoot"
}
$rec = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\reconcile_automation_registry.ps1"
if (-not (Test-Path -LiteralPath $rec)) {
    throw "reconcile script missing: $rec"
}

$reg = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\automation_registry.json"
$out = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\ops\automation_registry_reconcile_latest.json"

$args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $rec,
    "-RegistryPath", $reg,
    "-OutputPath", $out
)
if ($Enforce) { $args += "-Enforce" }
if ($ShowJson) { $args += "-ShowJson" }
if ($IgnoreExecutionHealth) { $args += "-IgnoreExecutionHealth" }

& powershell.exe @args
exit $LASTEXITCODE
