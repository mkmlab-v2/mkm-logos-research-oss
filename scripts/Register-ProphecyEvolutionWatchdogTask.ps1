#Requires -Version 5.1
<#
.SYNOPSIS
  Register a daily Task Scheduler job for prophecy evolution + B-track eval staleness watchdog.

.DESCRIPTION
  Runs scripts/Invoke-ProphecyEvolutionWatchdog_v1.ps1 (strict: missing ablation/hit-rate fails).
  Default: hit-rate streak guard (last N tail samples all at/below threshold) + staleness checks.
  Writes reports/prophecy_evolution_watchdog_latest.json + appends reports/prophecy_evolution_watchdog_hit_rate_tail_v1.jsonl (deduped).
  Failure webhook: PROPHECY_EVOLUTION_WATCHDOG_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-ProphecyEvolutionWatchdogTask.ps1" -At "10:15"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-ProphecyEvolutionWatchdogTask.ps1" -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Prophecy-Evolution-Watchdog",
    [string]$At = "10:15",
    [double]$MaxAblationAgeHours = 96,
    [double]$MaxHitRateAgeHours = 96,
    [int]$HitRateStreakCount = 3,
    [double]$HitRateStreakBelow = 0.40,
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-ProphecyEvolutionWatchdog_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing watchdog wrapper: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -MaxAblationAgeHours $MaxAblationAgeHours -MaxHitRateAgeHours $MaxHitRateAgeHours -HitRateStreakCount $HitRateStreakCount -HitRateStreakBelow $HitRateStreakBelow"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Daily prophecy evolution staleness + B-track hit-rate streak/tail + eval age; reports/prophecy_evolution_watchdog_latest.json"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime   : $($taskInfo.NextRunTime)"
Write-Host "  LastTaskResult: $($taskInfo.LastTaskResult)"
Write-Host "  LogonType     : $logonType"
Write-Host "  Action        : powershell.exe $argLine"
