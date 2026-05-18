#Requires -Version 5.1
<#
.SYNOPSIS
  Register a daily hidden Task Scheduler job for the full B-track daily hypothesis chain.

.DESCRIPTION
  Runs scripts/run_btrack_daily_hypothesis_chain.ps1 with -WindowStyle Hidden.
  Default scheduled args use -ResearchEvaluationInstrument multi (research tagging / dual-leg
  eval alignment). Trading policy in-chain remains BTC-only for execution semantics; see chain header.
  Prophecy contemplation pre-gate: **default ON** for the BTC research lane only (`-ResearchEvaluationInstrument btc`);
  use env MKM_BTRACK_PROPHECY_CONTEMPLATION_V1=0 to opt out. For multi/kospi scheduled runs the gate is skipped.
  When contemplation runs with MKM_BTRACK_CONTEMPLATION_USE_GEMINI=1 in .env, pass -SkipProphecyContemplationGemini on the chain to force `--skip-gemini-reflect` (local guards only; no API spend).
  By default the registered task passes -SkipPanel24hAlertsCheck to the chain so Check-ProphecyPanel24hAlerts.ps1
  (exit 1 on KPI miss / no_data) does not mark the whole scheduled job failed. Use -IncludePanel24hAlertsCheck only
  if you want the legacy single-task behavior (panel inside the same run).
  Optional second daily run: Register-ProphecyPanel24hAlertsTask.ps1 (e.g. 09:05) for panel snapshot / alerts after the chain.
  -SkipPanel24hAlertsCheck may still be passed for documentation parity with the chain script; it is redundant with the new default.
  Phase3 leading sensors (research_only): pass -IncludePhase3LeadingSensors to forward the chain switch; add
  -SkipPhase3NetworkFetch to skip Binance prefetch (join uses existing sensor stubs only).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35"

.EXAMPLE
  BTC research lane (contemplation pre-gate on by default; set MKM_BTRACK_PROPHECY_CONTEMPLATION_V1=0 in .env to opt out):
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35" -ResearchEvaluationInstrument btc

.EXAMPLE
  Include 30 trading-day OHLCV score rows in the same chain (heavier):
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35" -IncludeDawnScore

.EXAMPLE
  BTC lane but skip paid Gemini reflect on contemplation (keep local guards; .env may still set USE_GEMINI=1):
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35" -ResearchEvaluationInstrument btc -SkipProphecyContemplationGemini

.EXAMPLE
  Legacy: run the panel check inside the same task (not recommended; prefer Register-ProphecyPanel24hAlertsTask.ps1):
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35" -IncludePanel24hAlertsCheck

.EXAMPLE
  Phase3 leading-sensors join after hit-rate (no Binance prefetch):
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:35" -IncludePhase3LeadingSensors -SkipPhase3NetworkFetch

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
    # Opt in to running Check-ProphecyPanel24hAlerts inside the same scheduled task (legacy). Default omits it
    # (chain gets -SkipPanel24hAlertsCheck; use Register-ProphecyPanel24hAlertsTask.ps1 for a separate panel job).
    [switch]$IncludePanel24hAlertsCheck,
    # Legacy / explicit: default registration already skips the panel in-chain; do not combine with -IncludePanel24hAlertsCheck.
    [switch]$SkipPanel24hAlertsCheck,
    [switch]$SkipProphecyContemplationGemini,
    # Forward to run_btrack_daily_hypothesis_chain.ps1 (Phase3 leading-sensors hook; research_only).
    [switch]$IncludePhase3LeadingSensors,
    [switch]$SkipPhase3NetworkFetch,
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

if ($IncludePanel24hAlertsCheck -and $SkipPanel24hAlertsCheck) {
    throw "Use only one of -IncludePanel24hAlertsCheck or -SkipPanel24hAlertsCheck."
}

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -ResearchEvaluationInstrument $ResearchEvaluationInstrument"
if ($IncludeDawnScore) {
    $argLine += " -IncludeDawnScore"
}
if (-not $IncludePanel24hAlertsCheck) {
    $argLine += " -SkipPanel24hAlertsCheck"
}
if ($SkipProphecyContemplationGemini) {
    $argLine += " -SkipProphecyContemplationGemini"
}
if ($IncludePhase3LeadingSensors) {
    $argLine += " -IncludePhase3LeadingSensors"
}
if ($SkipPhase3NetworkFetch) {
    $argLine += " -SkipPhase3NetworkFetch"
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
