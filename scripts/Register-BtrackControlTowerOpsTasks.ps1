<#
.SYNOPSIS
  Register or remove scheduled tasks for B-track Control Tower ops.

.DESCRIPTION
  Creates two optional tasks:
  - Weekly control tower run (Mode weekly)
  - Daily bounded autopush run (Mode autopush)

  Defaults are HITL-safe and bounded.
#>
param(
    [switch]$Remove,
    [string]$WeeklyTaskName = "MKM_BTrack_ControlTower_Weekly",
    [string]$AutopushTaskName = "MKM_BTrack_ControlTower_Autopush_Daily",
    [string]$WeeklyMondayAt = "00:05",
    [string]$DailyAt = "01:10",
    [int]$AutopushMaxRuns = 3,
    [int]$AutopushCooldownSeconds = 60,
    [double]$AutopushMinAccuracyDelta = 0.0,
    [switch]$SkipPhase2,
    [switch]$DisableSignalLightRouting,
    [switch]$AutoApplyOnGoReady,
    [switch]$ApplyForce,
    [switch]$ApplyDryRun
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-BtrackControlTowerOps.ps1"

function Parse-At([string]$hhmm) {
    $parts = $hhmm -split ":"
    if ($parts.Count -lt 2) {
        throw "Invalid time format (HH:mm): $hhmm"
    }
    return Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $WeeklyTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $AutopushTaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed tasks (if existed): $WeeklyTaskName, $AutopushTaskName"
    exit 0
}

$weeklyAt = Parse-At $WeeklyMondayAt
$dailyAt = Parse-At $DailyAt

$skipArg = if ($SkipPhase2) { " -SkipPhase2" } else { "" }
$disableSignalRouteArg = if ($DisableSignalLightRouting) { " -DisableSignalLightRouting" } else { "" }
$autoApplyArg = if ($AutoApplyOnGoReady) { " -AutoApplyOnGoReady" } else { "" }
$applyForceArg = if ($ApplyForce) { " -ApplyForce" } else { "" }
$applyDryRunArg = if ($ApplyDryRun) { " -ApplyDryRun" } else { "" }

$weeklyArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Mode weekly$skipArg$disableSignalRouteArg$autoApplyArg$applyForceArg$applyDryRunArg"
$autopushArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Mode autopush -MaxRuns $AutopushMaxRuns -CooldownSeconds $AutopushCooldownSeconds -AutopushMinAccuracyDelta $AutopushMinAccuracyDelta$skipArg$autoApplyArg$applyForceArg$applyDryRunArg"

$weeklyAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $weeklyArgs -WorkingDirectory $workspaceRoot
$autopushAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $autopushArgs -WorkingDirectory $workspaceRoot

$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At $weeklyAt
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $dailyAt

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $WeeklyTaskName -Action $weeklyAction -Trigger $weeklyTrigger -Settings $settings -Principal $principal -Description "B-track Control Tower weekly run (HITL-safe)." -Force | Out-Null
Register-ScheduledTask -TaskName $AutopushTaskName -Action $autopushAction -Trigger $dailyTrigger -Settings $settings -Principal $principal -Description "B-track Control Tower bounded daily autopush." -Force | Out-Null

# Health snapshot treats Disabled as ops_not_ready; (re-)register implies tasks should be runnable.
Enable-ScheduledTask -TaskPath '\' -TaskName $WeeklyTaskName -ErrorAction SilentlyContinue | Out-Null
Enable-ScheduledTask -TaskPath '\' -TaskName $AutopushTaskName -ErrorAction SilentlyContinue | Out-Null

Write-Host "Registered: $WeeklyTaskName (Mon $WeeklyMondayAt)"
Write-Host "Registered: $AutopushTaskName (Daily $DailyAt, MaxRuns=$AutopushMaxRuns)"
Write-Host "Runner: $runner"
