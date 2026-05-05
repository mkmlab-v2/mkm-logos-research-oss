<#
.SYNOPSIS
  Register (or remove) a daily task for execution insight brief generation.

.DESCRIPTION
  Schedules scripts/Run-DailyExecutionInsightBrief_v1.ps1 once per day.
  Default runs in observation mode and writes reports/daily_execution_insight_brief_latest.md.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_DailyExecutionInsightBrief",
    [string]$DailyAt = "07:20",
    [switch]$DatedCopy,
    [switch]$SkipIndependentLensRefresh,
    [switch]$SkipFusionRefresh,
    [switch]$SkipLogosTrackBDeepReport,
    [switch]$SkipThinRefresh,
    [switch]$SkipMyeongniThinBridge,
    [switch]$SkipMyeongriV2Upgrade
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-DailyExecutionInsightBrief_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 07:20), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`""
)
if ($DatedCopy) { $runnerArgs += "-DatedCopy" }
if ($SkipIndependentLensRefresh) { $runnerArgs += "-SkipIndependentLensRefresh" }
if ($SkipFusionRefresh) { $runnerArgs += "-SkipFusionRefresh" }
if ($SkipLogosTrackBDeepReport) { $runnerArgs += "-SkipLogosTrackBDeepReport" }
if ($SkipThinRefresh) { $runnerArgs += "-SkipThinRefresh" }
if ($SkipMyeongniThinBridge) { $runnerArgs += "-SkipMyeongniThinBridge" }
if ($SkipMyeongriV2Upgrade) { $runnerArgs += "-SkipMyeongriV2Upgrade" }
$argLine = $runnerArgs -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily Fact-Lock execution insight brief chain (Run-DailyExecutionInsightBrief_v1.ps1)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Argument: $argLine"
