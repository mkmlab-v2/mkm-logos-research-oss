<#
.SYNOPSIS
  Register weekly Scheduled Task for cost-optimized marketing bundle (tier_0 default, no -Gemini).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_Marketing_WeeklyDraftBundle

.PARAMETER MondayAt
  Local time HH:mm (default 09:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Marketing_WeeklyDraftBundle",
    [string]$MondayAt = "09:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    "C:\workspace"
}
$runner = Join-Path $workspaceRoot "scripts\Run-MarketingWeeklyDraftBundle_v1.ps1"

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
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 45)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = @"
Weekly marketing bundle (tier_0): sync marketing_content_queue -> LinkedIn assemble-only + copy guard.
No API publish. Optional Gemini only when MKM_MARKETING_GEMINI_ALLOWED=1 and queue allow_gemini.
SSOT: docs/final/artifacts/marketing_ops_cost_tier_v1_latest.json
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (Monday $MondayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: scripts\Verify-MarketingWeeklyDraftBundleTaskReadiness_v1.ps1"
Write-Host "Legacy LinkedIn-only task MKM_LinkedIn_B2B_WeeklyDraft may be removed if duplicate."
