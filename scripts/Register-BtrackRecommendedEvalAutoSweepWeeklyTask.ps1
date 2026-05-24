#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task: B-track recommended eval neutral_bps auto-sweep + apply.

.DESCRIPTION
  Runs scripts/Run-BtrackRecommendedEvalAutoSweep_v1.ps1 (wraps
  run_prophecy_btrack_recommended_eval_chain_v1.py --auto-sweep-and-apply).
  Default: Sunday 09:45 local — after MKM-BTrack-BtcWeight-HitRateBundle-Weekly (09:15) if both registered.
  B-track measurement only; human gate still applies for strict promotion.

.PARAMETER Remove
  Unregister the task.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BtrackRecommendedEvalAutoSweepWeeklyTask.ps1"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BtrackRecommendedEvalAutoSweepWeeklyTask.ps1" -SundayAt "10:00" -RunWhenLoggedOff

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BtrackRecommendedEvalAutoSweepWeeklyTask.ps1" -Remove
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-BTrack-RecommendedEval-AutoSweep-Weekly",
    [string]$SundayAt = "09:45",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$AutoSweepGrid = "",
    [switch]$RunWhenLoggedOff,
    [switch]$AlignPromotionPushPanel
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-BtrackRecommendedEvalAutoSweep_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner script: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 09:45), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""
if ($AutoSweepGrid) {
    $argLine += " -AutoSweepGrid `"$AutoSweepGrid`""
}
if ($AlignPromotionPushPanel) {
    $argLine += " -AlignPromotionPushPanel"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -MultipleInstances IgnoreNew `
    -Hidden

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Weekly B-track: recommended eval chain auto neutral_bps sweep + apply -> reports/*_recommended*_latest* ([HYPO] only)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime   : $($taskInfo.NextRunTime)"
Write-Host "  SundayAt      : $SundayAt"
Write-Host "  AutoSweepGrid : $(if ($AutoSweepGrid) { $AutoSweepGrid } else { '(default)' })"
