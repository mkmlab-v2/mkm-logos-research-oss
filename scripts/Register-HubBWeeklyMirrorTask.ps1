<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task to run Invoke-HubBWeeklyMirror.ps1 (Saturday default).

.DESCRIPTION
  Requires: G: vault available when task runs (interactive user + mapped drive per org policy).
  Run elevated if Register-ScheduledTask fails for your account.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_HubB_WeeklyMirror).

.PARAMETER SaturdayAt
  Local time HH:mm for weekly Saturday trigger (default: 08:30).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_HubB_WeeklyMirror",
    [string]$SaturdayAt = "08:30"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-HubBWeeklyMirror.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SaturdayAt -split ':'
if ($parts.Count -lt 2) {
    throw "SaturdayAt must be HH:mm (e.g. 08:30), got: $SaturdayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`"" `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Saturday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 60)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly Hub B prep: vault mirror (NotebookLM SSOT) + reports/hub_b_weekly_mirror_log.jsonl. Cloud Hub B upload is manual/MCP after mirror."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Saturday $SaturdayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
