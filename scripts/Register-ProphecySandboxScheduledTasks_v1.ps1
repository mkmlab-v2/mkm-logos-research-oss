#Requires -Version 5.1
<#
.SYNOPSIS
  Register MKM Prophecy Sandbox daily (08:50) + weekly Phase3 (Sat 08:45) tasks.

.NOTES
  research_only — never mutates prod btrack_prophecy_score_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$Unregister,
    [switch]$DryRun,
    [switch]$SkipWeekly,
    [switch]$WeeklyWithBinance,
    [switch]$NoBackfillStreamCalendar,
    [switch]$SyncDailyThreadLog,
    [int]$DailyThread = 5,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$daily = Join-Path $WorkspaceRoot "scripts\Register-ProphecySandboxDailyTask.ps1"
$weekly = Join-Path $WorkspaceRoot "scripts\Register-ProphecySandboxWeeklyPhase3Task.ps1"

if (-not (Test-Path -LiteralPath $daily)) { throw "Missing: $daily" }

$common = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File")

if ($DryRun) {
    Write-Host "=== Daily ==="
    $dailyDry = @($daily, "-WorkspaceRoot", $WorkspaceRoot, "-DryRun")
    if ($NoBackfillStreamCalendar) { $dailyDry += "-NoBackfillStreamCalendar" }
    if ($SyncDailyThreadLog) {
        $dailyDry += "-SyncDailyThreadLog"
        $dailyDry += "-DailyThread"
        $dailyDry += "$DailyThread"
    }
    & powershell @common @dailyDry
    if (-not $SkipWeekly) {
        Write-Host "=== Weekly ==="
        $wArgs = @($weekly, "-WorkspaceRoot", $WorkspaceRoot, "-DryRun")
        if ($WeeklyWithBinance) { $wArgs += "-RefreshPhase3Binance" }
        & powershell @common @wArgs
    }
    exit 0
}

if ($Unregister) {
    & powershell @common $daily -WorkspaceRoot $WorkspaceRoot -Unregister
    if (-not $SkipWeekly) {
        & powershell @common $weekly -WorkspaceRoot $WorkspaceRoot -Unregister
    }
    Write-Host "Unregistered Prophecy Sandbox scheduled tasks"
    exit 0
}

$dailyArgs = @($daily, "-WorkspaceRoot", $WorkspaceRoot)
if ($NoBackfillStreamCalendar) { $dailyArgs += "-NoBackfillStreamCalendar" }
if ($SyncDailyThreadLog) {
    $dailyArgs += "-SyncDailyThreadLog"
    $dailyArgs += "-DailyThread"
    $dailyArgs += "$DailyThread"
}
if ($RunWhenLoggedOff) { $dailyArgs += "-RunWhenLoggedOff" }
& powershell @common @dailyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipWeekly) {
    if (-not (Test-Path -LiteralPath $weekly)) { throw "Missing: $weekly" }
    $wArgs = @($weekly, "-WorkspaceRoot", $WorkspaceRoot)
    if ($WeeklyWithBinance) { $wArgs += "-RefreshPhase3Binance" }
    if ($RunWhenLoggedOff) { $wArgs += "-RunWhenLoggedOff" }
    & powershell @common @wArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Registered Prophecy Sandbox scheduled tasks (daily + weekly unless -SkipWeekly)"
