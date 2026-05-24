#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly O-P30 open-beta traffic rollup (probe history → MD/JSON).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Op30_MagicOrb_Traffic_Weekly",
    [string]$WeeklyAt = "08:05",
    [ValidateSet("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")]
    [string]$DayOfWeek = "Sunday"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$rollup = Join-Path $workspaceRoot "scripts\build_magic_orb_open_beta_weekly_rollup_v1.py"
$phase4 = Join-Path $workspaceRoot "scripts\Invoke-Op30Phase4TrafficObservability_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$autoRun = Join-Path $workspaceRoot "scripts\Invoke-Op30AutoRun_v1.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"& '$autoRun' -FullParallel -SkipLivePatrol`"" `
    -WorkingDirectory $workspaceRoot

$dow = [System.DayOfWeek]::$DayOfWeek
$parts = $WeeklyAt -split ':'
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $dow -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "O-P30 weekly: AutoRun FullParallel + rollup. [HYPO] B-track."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName $DayOfWeek at $WeeklyAt"
Write-Host "Remove: powershell -File scripts\Register-Op30MagicOrbTrafficWeeklyTask.ps1 -Remove"
