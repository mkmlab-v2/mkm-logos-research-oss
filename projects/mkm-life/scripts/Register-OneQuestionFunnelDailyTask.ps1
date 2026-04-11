<#
.SYNOPSIS
  Register (or remove) a daily Windows Scheduled Task for the mkmlife one-question funnel chain.

.DESCRIPTION
  Runs npm from the mkm-life package root so package.json scripts (env + paths) match local dev.
  Default npm script: check:one-question:funnel-chain:realdata (REQUIRE_REAL_DATA_GATE + synthetic cap).
  With -AllowSynthetic: check:one-question:funnel-chain (no real-data gate in script).

.PARAMETER Remove
  Unregister the task.

.PARAMETER AllowSynthetic
  Schedule check:one-question:funnel-chain instead of :realdata.

.PARAMETER TaskName
  Scheduled task name (default: MKM_MKMLife_OneQuestionFunnel_Daily).

.PARAMETER DailyAt
  Local time HH:mm for the daily trigger (default: 06:30).
#>
param(
    [switch]$Remove,
    [switch]$AllowSynthetic,
    [string]$TaskName = "MKM_MKMLife_OneQuestionFunnel_Daily",
    [string]$DailyAt = "06:30"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mkmLifeRoot = Split-Path -Parent $scriptDir
$pkg = Join-Path $mkmLifeRoot "package.json"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $pkg)) {
    throw "package.json not found (wrong cwd?): $pkg"
}

$npmScript = if ($AllowSynthetic) { "check:one-question:funnel-chain" } else { "check:one-question:funnel-chain:realdata" }

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:30), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$inner = "Set-Location -LiteralPath '$mkmLifeRoot'; npm run $npmScript; exit `$LASTEXITCODE"
$argLine = "-NoProfile -ExecutionPolicy Bypass -Command `"$inner`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $mkmLifeRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$mode = if ($AllowSynthetic) { "allow-synthetic (no real-data gate script)" } else { "realdata gate (npm :realdata)" }
$description = "Daily mkmlife one-question funnel: npm run $npmScript ($mode). See package.json check:one-question:*."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "WorkingDirectory: $mkmLifeRoot"
Write-Host "npm run $npmScript"
