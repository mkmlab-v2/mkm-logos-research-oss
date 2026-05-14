#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or remove) weekly Scheduled Task: Aramaic MVP alert threshold sweep → apply.

.DESCRIPTION
  Runs scripts/Run-AramaicMvpThresholdWeeklyChain_v1.ps1. Default: Sunday 08:40 local.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-AramaicMvp-Threshold-Weekly",
    [string]$SundayAt = "08:40",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-AramaicMvpThresholdWeeklyChain_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 08:40), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 35) `
    -MultipleInstances IgnoreNew `
    -Hidden

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Weekly Aramaic MVP alert threshold sweep → recommended artifact (B-track)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime: $($info.NextRunTime)"
Write-Host "  SundayAt   : $SundayAt"
