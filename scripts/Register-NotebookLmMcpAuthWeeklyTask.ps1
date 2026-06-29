<#
.SYNOPSIS
  Register weekly Scheduled Task: NotebookLM MCP auth auto-repair (nlm + cookie sync).

.DESCRIPTION
  Runs Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1 — tier_0, no paid API.
  Default: Sunday 07:45 (before compression governance 07:00 band / chronology 08:30 / HD AE 09:15).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_NotebookLm_McpAuth_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default: 07:45).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_NotebookLm_McpAuth_Weekly",
    [string]$SundayAt = "07:45"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$runner = Join-Path $workspaceRoot "scripts\Invoke-NotebookLmMcpAuthAutoRepair_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 07:45), got: $SundayAt"
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
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly: nlm login check + sync cookies to notebooklm-mcp state.json + get_health probe (tier_0)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
