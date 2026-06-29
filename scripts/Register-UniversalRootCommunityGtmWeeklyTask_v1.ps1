#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: Universal Root community GTM poll + gated Thread B auto-post.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_UniversalRoot_CommunityGtm_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default: 11:00 — after deployment axis isolation 10:10).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_UniversalRoot_CommunityGtm_Weekly",
    [string]$SundayAt = "11:00"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$runner = Join-Path $workspaceRoot "scripts\Invoke-UniversalRootCommunityGtmWeeklyRoutine_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SundayAt must be HH:mm (e.g. 11:00), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = @"
Weekly UR-W1 community GTM: poll GitHub Discussions #2; auto Thread B when external_repro>=1 (send_gate HOLD ack in runner).
[HYPO] B-track — requires gh auth for poll/post.
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: powershell -File scripts\Verify-UniversalRootCommunityGtmWeeklyScheduledTask_v1.ps1"
Write-Host "Manual: powershell -File scripts\Invoke-UniversalRootCommunityGtmWeeklyRoutine_v1.ps1"
