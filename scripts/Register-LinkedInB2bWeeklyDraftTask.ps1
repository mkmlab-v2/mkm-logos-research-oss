<#
.SYNOPSIS
  Register (or remove) weekly Scheduled Task for LinkedIn B2B draft chain (assemble-only; no publish).

.DESCRIPTION
  Runs scripts/run_linkedin_b2b_weekly_draft_chain_v1.ps1 — local queue, copy guard, no1kmedi marketing-copy check.
  Human LinkedIn publish only after legal sign-off ([DRAFT]).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_LinkedIn_B2B_WeeklyDraft

.PARAMETER MondayAt
  Local time HH:mm for weekly Monday trigger (default: 09:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_LinkedIn_B2B_WeeklyDraft",
    [string]$MondayAt = "09:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    "C:\workspace"
}
$runner = Join-Path $workspaceRoot "scripts\run_linkedin_b2b_weekly_draft_chain_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $MondayAt -split ':'
if ($parts.Count -lt 2) {
    throw "MondayAt must be HH:mm (e.g. 09:00), got: $MondayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly LinkedIn B2B draft queue: assemble-only + copy guard. No API publish. Output: reports/marketing/linkedin_drafts."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Monday $MondayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: scripts\Verify-LinkedInB2bWeeklyDraftTaskReadiness.ps1"
