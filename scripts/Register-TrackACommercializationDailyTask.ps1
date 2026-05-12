#Requires -Version 5.1
<#
.SYNOPSIS
  Register (or remove) a daily Windows Scheduled Task for the Track A commercialization chain.

.DESCRIPTION
  Runs scripts/run_track_a_commercialization_daily_chain.ps1 (shadow → metering → weekly → band gate
  → cost sim → signal light) and appends reports/track_a_commercialization_daily_log.jsonl.

.NOTES
  Default GateMode is warning (band gate exit 3 does not fail the task).
  Register-ScheduledTask may require an elevated PowerShell on some hosts; use -DryRun to inspect.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_TrackA_CommercializationDaily",
    [string]$DailyAt = "07:22",
    [ValidateSet("warning", "block")]
    [string]$GateMode = "warning",
    [switch]$DryRun,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$chain = Join-Path $PSScriptRoot "run_track_a_commercialization_daily_chain.ps1"

if (-not (Test-Path -LiteralPath $chain)) {
    throw "Chain script not found: $chain"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 07:22), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$chain`"",
    "-WorkspaceRoot", "`"$repoRoot`"",
    "-GateMode", $GateMode
)
$argLine = $runnerArgs -join " "

if ($DryRun) {
    Write-Host "DRY_RUN: would register task=$TaskName daily_at=$DailyAt gate_mode=$GateMode"
    Write-Host "working_directory=$repoRoot"
    Write-Host "powershell.exe $argLine"
    if ($StartNow) { Write-Host "DRY_RUN: StartNow ignored" }
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 25)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Track A commercialization daily chain (shadow, metering, weekly, band gate, cost sim, signal light)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $DailyAt, GateMode=$GateMode, user=$env:USERNAME)"
Write-Host "Chain: $chain"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Started scheduled task: $TaskName"
}
