<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for MKM AI v2 readiness checks.

.DESCRIPTION
  Runs Invoke-MkmAiV2DailyReadiness.ps1 and appends JSONL log rows to reports/mkm_ai_v2_readiness_log.jsonl.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_AIV2_DailyReadiness",
    [string]$DailyAt = "07:10",
    [switch]$IncludeDualLegDashboardChain,
    [int]$DualLegRecentTradingDays = 30,
    [switch]$EnableFallbackPostCutoffCriticalFail,
    [double]$FallbackPostCutoffWarnRate = 0.15,
    [switch]$IncludeLgHSPersuasionBridge,
    [ValidateSet("general", "performance", "safety", "schedule")]
    [string]$LgHSPersuasionQuestionType = "safety"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-MkmAiV2DailyReadiness.ps1"

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
    throw "DailyAt must be HH:mm (e.g. 07:10), got: $DailyAt"
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
if ($IncludeDualLegDashboardChain) {
    $runnerArgs += "-IncludeDualLegDashboardChain"
    $runnerArgs += @("-DualLegRecentTradingDays", "$DualLegRecentTradingDays")
}
if ($EnableFallbackPostCutoffCriticalFail) {
    $runnerArgs += "-EnableFallbackPostCutoffCriticalFail"
}
$runnerArgs += @("-FallbackPostCutoffWarnRate", "$FallbackPostCutoffWarnRate")
if ($IncludeLgHSPersuasionBridge) {
    $runnerArgs += "-IncludeLgHSPersuasionBridge"
    $runnerArgs += @("-LgHSPersuasionQuestionType", "$LgHSPersuasionQuestionType")
}
$argLine = $runnerArgs -join " "

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily MKM AI v2 readiness gate; writes readiness artifacts/log. Optional dual-leg and LG HS persuasion bridge artifacts can be refreshed."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Argument: $argLine"
