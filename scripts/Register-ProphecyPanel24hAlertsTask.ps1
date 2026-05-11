#Requires -Version 5.1
<#
.SYNOPSIS
  Register a daily hidden Task Scheduler job for panel 24h alert checks.

.DESCRIPTION
  Runs scripts/Check-ProphecyPanel24hAlerts.ps1 after the daily B-track chain (default 09:05).
  Writes reports/prophecy_panel_24h_alerts_latest.json and appends reports/prophecy_panel_24h_alerts_log.jsonl.
  On failure (exit 1), optional webhook: User env PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL (same as other OPS scripts).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-ProphecyPanel24hAlertsTask.ps1" -At "09:05"

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-ProphecyPanel24hAlertsTask.ps1" -Remove
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-Prophecy-Panel-24h-Alerts",
    [string]$At = "09:05",
    [double]$MinHitRate = 0.60,
    [switch]$RunWhenLoggedOff,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Check-ProphecyPanel24hAlerts.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing checker script: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "[DONE] Removed task (if existed): $TaskName" -ForegroundColor Yellow
    exit 0
}

$outJson = Join-Path $WorkspaceRoot "reports\prophecy_panel_24h_alerts_latest.json"
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -MinHitRate $MinHitRate -OutJson `"$outJson`" -AppendLog"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew -Hidden
$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited
$desc = "Daily panel 24h alert check; exit 1 on failure (Task Scheduler LastTaskResult)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $desc -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host "[DONE] Registered task: $TaskName" -ForegroundColor Green
Write-Host "  NextRunTime   : $($taskInfo.NextRunTime)"
Write-Host "  LastTaskResult: $($taskInfo.LastTaskResult)"
Write-Host "  LogonType     : $logonType"
Write-Host "  Action        : powershell.exe $argLine"
