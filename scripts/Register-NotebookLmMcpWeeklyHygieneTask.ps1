#Requires -Version 5.1
<#
.SYNOPSIS
  Register a weekly scheduled task that runs repair_notebooklm_mcp_auth_stuck.ps1 (stale Chrome + stale node/cmd).

.DESCRIPTION
  Prevents accumulation of zombie notebooklm-mcp processes that block MCP handshake after Cursor restarts.
  Complements logoff repair (scripts/register_notebooklm_mcp_repair_logoff_task.ps1).

.PARAMETER Remove
  Unregister the weekly task only.

.NOTES
  Runs as current user (Limited). Does not call setup_auth or touch cookies.
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_NotebookLmMcpWeeklyHygiene",
    [int]$StaleNodeMaxHours = 12,
    [System.DayOfWeek]$DayOfWeek = [System.DayOfWeek]::Sunday,
    [string]$AtLocalTime = "07:00"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\repair_notebooklm_mcp_auth_stuck.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -StaleNodeMaxHours $StaleNodeMaxHours"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Weekly: $DayOfWeek at $AtLocalTime (local)"
Write-Host "  Runner: $runner"
Write-Host "  StaleNodeMaxHours: $StaleNodeMaxHours"
Write-Host ""
Write-Host "Optional: also register logoff cleanup:" -ForegroundColor Cyan
Write-Host "  powershell -File `"$(Join-Path $WorkspaceRoot 'scripts\register_notebooklm_mcp_repair_logoff_task.ps1')`""
