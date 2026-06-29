<#
.SYNOPSIS
  Register weekly Scheduled Task for commander interest benchmark + AI-native briefing chain.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_CommanderInterestBenchmark_Weekly

.PARAMETER MondayAt
  Local time HH:mm (default 08:30, before marketing bundle).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CommanderInterestBenchmark_Weekly",
    [string]$MondayAt = "08:30"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    "C:\workspace"
}
$runner = Join-Path $workspaceRoot "scripts\Run-CommanderInterestBenchmarkChain_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $MondayAt -split ':'
if ($parts.Count -lt 2) { throw "MondayAt must be HH:mm, got: $MondayAt" }
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = @"
Weekly commander interest benchmark: inbox ingest -> weekly TOP-N report -> AI-native briefing (card + podcast script) -> Telegram digest (skip if unset).
Internal observation only; human_publish_only; send_gate HOLD. No patient-facing auto copy.
SSOT: docs/final/artifacts/commander_interest_benchmark_config_v1.default.json
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (Monday $MondayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: scripts\Verify-CommanderInterestBenchmarkWeeklyTaskReadiness_v1.ps1"
