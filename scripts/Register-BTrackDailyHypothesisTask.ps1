#Requires -Version 5.1
<#
.SYNOPSIS
  Register a daily hidden Task Scheduler job for the full B-track daily hypothesis chain.

.DESCRIPTION
  Runs scripts/run_btrack_daily_hypothesis_chain.ps1 with -WindowStyle Hidden.
  Default scheduled args use -ResearchEvaluationInstrument multi (research tagging / dual-leg
  eval alignment). Trading policy in-chain remains BTC-only for execution semantics; see chain header.
  The chain ends with Check-ProphecyPanel24hAlerts.ps1 (unless -SkipPanel24hAlertsCheck is added to args).
  Optional second daily run: Register-ProphecyPanel24hAlertsTask.ps1 (e.g. 09:05) for a later snapshot or if chain args skip the check.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35"

.EXAMPLE
  Include 30 trading-day OHLCV score rows in the same chain (heavier):
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35" -IncludeDawnScore

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-BTrack-DailyHypothesis-Chain",
    [string]$At = "08:35",
    [ValidateSet("btc", "kospi", "multi")]
    [string]$ResearchEvaluationInstrument = "multi",
    [switch]$IncludeDawnScore,
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing chain script: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -ResearchEvaluationInstrument $ResearchEvaluationInstrument"
if ($IncludeDawnScore) {
    $argLine += " -IncludeDawnScore"
}
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 3) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Hidden daily run: run_btrack_daily_hypothesis_chain.ps1 (B-track research; not live trading)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime   : $($taskInfo.NextRunTime)"
Write-Host "  LastTaskResult: $($taskInfo.LastTaskResult)"
Write-Host "  LogonType     : $logonType"
Write-Host "  Action        : powershell.exe $argLine"
