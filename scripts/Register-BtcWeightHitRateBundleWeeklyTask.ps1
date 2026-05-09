#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task: BTC weight profiles × OHLCV hit-rate bundle report.

.DESCRIPTION
  Runs scripts/Run-BtcWeightWeeklyHitRateBundle_v1.ps1 (B-track measurement only; no live trading).
  Default: Sunday 09:15 local — after typical daily OHLCV chains; adjust -SundayAt if needed.
  By default does NOT pass -ApplyWinner (ensemble JSON unchanged); use -ApplyWinner to promote weights.

.PARAMETER Remove
  Unregister the task.

.PARAMETER ApplyWinner
  If set, scheduled action includes -ApplyWinner (writes hit-rate winner into btrack_lens_ensemble_v1.json).

.PARAMETER RefreshMarketData
  If set, passes -RefreshMarketData (yfinance fetch; network).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BtcWeightHitRateBundleWeeklyTask.ps1"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BtcWeightHitRateBundleWeeklyTask.ps1" -SundayAt "09:30" -ApplyWinner

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BtcWeightHitRateBundleWeeklyTask.ps1" -Remove
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-BTrack-BtcWeight-HitRateBundle-Weekly",
    [string]$SundayAt = "09:15",
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$RecentTradingDays = 30,
    [int]$MinEvalRows = 5,
    [switch]$ApplyWinner,
    [switch]$RefreshMarketData,
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-BtcWeightWeeklyHitRateBundle_v1.ps1"
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
    throw "SundayAt must be HH:mm (e.g. 09:15), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -RecentTradingDays $RecentTradingDays -MinEvalRows $MinEvalRows"
if ($ApplyWinner) { $argLine += " -ApplyWinner" }
if ($RefreshMarketData) { $argLine += " -RefreshMarketData" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -Hidden

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Weekly B-track: BTC ensemble weight sweep × OHLCV → reports/btrack_btc_weight_hit_rate_bundle_latest.json ([HYPO] only)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime   : $($taskInfo.NextRunTime)"
Write-Host "  SundayAt      : $SundayAt"
Write-Host "  ApplyWinner   : $ApplyWinner"
Write-Host "  RefreshMarket : $RefreshMarketData"
