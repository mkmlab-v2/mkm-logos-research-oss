#Requires -Version 5.1
<#
.SYNOPSIS
  Daily Prophecy Sandbox (08:50 local, after Phase3 ~09:10 optional ordering).

.NOTES
  research_only — never mutates prod btrack_prophecy_score_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$At = "08:50",
    [string]$TaskName = "MKM-Prophecy-Sandbox-DailyChain",
    [switch]$Unregister,
    [switch]$DryRun,
    [switch]$NoRefreshPhase3Join,
    [switch]$RefreshPhase3Binance,
    [switch]$NoBackfillStreamCalendar,
    [switch]$SyncDailyThreadLog,
    [int]$DailyThread = 5,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$script = Join-Path $WorkspaceRoot "scripts\run_prophecy_sandbox_daily_chain_v1.py"
$argParts = @("`"$script`"")
if (-not $NoRefreshPhase3Join) {
    $argParts += "--refresh-phase3-join"
}
if ($RefreshPhase3Binance) {
    $argParts += "--refresh-phase3-binance"
}
if (-not $NoBackfillStreamCalendar) {
    $argParts += "--backfill-stream-calendar"
}
if ($SyncDailyThreadLog) {
    $argParts += "--sync-daily-thread-log"
    $argParts += "--daily-thread"
    $argParts += "$DailyThread"
}
$argStr = $argParts -join " "

if ($DryRun) {
    Write-Host "TaskName=$TaskName At=$At Args=$argStr"
    exit 0
}

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Unregistered $TaskName"
    exit 0
}

$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action (
    New-ScheduledTaskAction -Execute "py.exe" -Argument $argStr -WorkingDirectory $WorkspaceRoot
) -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered $TaskName daily at $At (LogonType=$logonType)"
Write-Host "Args: $argStr"
