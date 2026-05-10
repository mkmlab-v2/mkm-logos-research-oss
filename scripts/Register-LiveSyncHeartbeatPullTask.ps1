#Requires -Version 5.1
<#
.SYNOPSIS
  Register scheduled task: Invoke-LiveSyncHeartbeatPull.ps1 (SCP pull every N minutes).

.PARAMETER Remove
  Unregister task.

.PARAMETER IntervalMinutes
  Default 5.

.PARAMETER SoftFail
  Pass -SoftFail to pull script (recommended for unattended).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-LiveSyncHeartbeatPullTask.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-LiveSyncHeartbeatPullTask.ps1 -IntervalMinutes 3 -SoftFail
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-LiveSync-Heartbeat-Pull",
    [int]$IntervalMinutes = 5,
    [switch]$SoftFail,
    [switch]$SkipHeartbeatCheck
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-LiveSyncHeartbeatPull.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed: $TaskName"
    exit 0
}

$sf = if ($SoftFail) { " -SoftFail" } else { "" }
$sk = if ($SkipHeartbeatCheck) { " -SkipHeartbeatCheck" } else { "" }
$interval = [Math]::Max(1, $IntervalMinutes)
$logPath = Join-Path $WorkspaceRoot "reports\live_sync_pull_schedule.log"
$runCmd = "cmd.exe /c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`"$sf$sk >> `"$logPath`" 2>&1"

schtasks /Create /TN $TaskName /TR $runCmd /SC MINUTE /MO $interval /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks /Create failed for $TaskName (exit=$LASTEXITCODE)"
}

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Every $interval minutes"
Write-Host "  Runner: $runner"
Write-Host "  Log: $WorkspaceRoot\reports\live_sync_pull_schedule.log"
Write-Host "  SoftFail: $SoftFail"
