#Requires -Version 5.1
<#
.SYNOPSIS
  Register Prophecy Sandbox daily (with thread log sync) + weekly Phase3 tasks.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun,
    [switch]$Unregister,
    [switch]$NoSyncDailyThreadLog,
    [int]$DailyThread = 5,
    [switch]$WeeklyWithBinance
)

$ErrorActionPreference = "Stop"
$bundle = Join-Path $PSScriptRoot "Register-ProphecySandboxScheduledTasks_v1.ps1"
if (-not (Test-Path -LiteralPath $bundle)) { throw "Missing: $bundle" }

$args = @("-WorkspaceRoot", $WorkspaceRoot)
if ($DryRun) { $args += "-DryRun" }
if ($Unregister) { $args += "-Unregister" }
if (-not $NoSyncDailyThreadLog) {
    $args += "-SyncDailyThreadLog"
    $args += "-DailyThread"
    $args += "$DailyThread"
}
if ($WeeklyWithBinance) { $args += "-WeeklyWithBinance" }

& powershell -NoProfile -ExecutionPolicy Bypass -File $bundle @args
exit $LASTEXITCODE
