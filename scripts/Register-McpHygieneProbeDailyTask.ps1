#Requires -Version 5.1
<#
.SYNOPSIS
  Register a daily scheduled task: Invoke-McpHygieneProbe (JSON to reports/, optional log).

.DESCRIPTION
  Prereq-only by default (no -Repair). Override with -IncludeRepair on registration.

.PARAMETER Remove
  Unregister the task.

.NOTES
  Task runs under current user. Log file append for audit trail.
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_McpHygieneProbe_Daily",
    [string]$AtLocalTime = "08:30",
    [switch]$IncludeRepair
)

$ErrorActionPreference = "Stop"

$probe = Join-Path $WorkspaceRoot "scripts\Invoke-McpHygieneProbe.ps1"
$outJson = Join-Path $WorkspaceRoot "reports\mcp_hygiene_probe_latest.json"
$log = Join-Path $WorkspaceRoot "reports\mcp_hygiene_probe_daily.log"

if (-not (Test-Path -LiteralPath $probe)) {
    throw "Probe script missing: $probe"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$repairArg = if ($IncludeRepair) { " -Repair" } else { "" }
# cmd wrapper: capture probe + prereq chatter to log; JSON still written via -OutJson
$cmdArgs = "/c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$probe`" -WorkspaceRoot `"$WorkspaceRoot`"$repairArg -OutJson `"$outJson`" >> `"$log`" 2>&1"

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Daily at $AtLocalTime (local)"
Write-Host "  JSON: $outJson"
Write-Host "  Log : $log"
Write-Host "  Repair: $IncludeRepair"
