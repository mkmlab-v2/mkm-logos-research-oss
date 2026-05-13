#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly scheduled task: Hostinger full-exit stabilization cycle (probe + optional Cloudflare health).

.PARAMETER Remove
  Unregister the task only.

.PARAMETER DryRun
  Print actions only.

.PARAMETER SkipCloudflareHealth
  Pass through to Invoke-HostingerFullExitStabilizationCycle_v1.ps1 (shorter runs, no token needed).

.NOTES
  Default: Monday 09:05 local. Adjust DayOfWeek / AtLocalTime as needed.
#>
param(
    [switch]$Remove,
    [switch]$DryRun,
    [switch]$SkipCloudflareHealth,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_HostingerFullExitStabilizationWeekly",
    [System.DayOfWeek]$DayOfWeek = [System.DayOfWeek]::Monday,
    [string]$AtLocalTime = "09:05"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-HostingerFullExitStabilizationCycle_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$flag = if ($SkipCloudflareHealth) { " -SkipCloudflareHealth" } else { "" }
$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"$flag"

if ($DryRun) {
    Write-Host "[DryRun] TaskName=$TaskName"
    Write-Host "[DryRun] powershell.exe $argLine"
    Write-Host "[DryRun] Weekly $DayOfWeek at $AtLocalTime"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Weekly: $DayOfWeek at $AtLocalTime (local)"
Write-Host "  Runner: $runner"
Write-Host "  Args: $argLine"
