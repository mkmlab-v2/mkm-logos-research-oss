#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot check for Athena automation scope (Task Scheduler vs automation_registry.json).

.DESCRIPTION
  Wraps projects/bitcoin-trading/ops/windows-rehearsal/reconcile_automation_registry.ps1.
  Tasks with optional=true and missing from the scheduler do not count as drift.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-AthenaAutomationRegistryCheck.ps1
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

$invokeArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $rec,
    "-RegistryPath", $reg,
    "-OutputPath", $out
)
if ($Enforce) { $invokeArgs += "-Enforce" }
if ($ShowJson) { $invokeArgs += "-ShowJson" }
if ($IgnoreExecutionHealth) { $invokeArgs += "-IgnoreExecutionHealth" }

& powershell.exe @invokeArgs
exit $LASTEXITCODE
