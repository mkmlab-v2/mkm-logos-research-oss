#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: mkmlife CF vs jema-ai/logos DNS deploy-axis isolation probe.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_Deployment_Axis_Isolation_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default: 10:10 — after Oracle module observability 09:45).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Deployment_Axis_Isolation_Weekly",
    [string]$SundayAt = "10:10"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$runner = Join-Path $workspaceRoot "scripts\Invoke-MkmDeploymentAxisIsolationWeeklyRoutine_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 10:10), got: $SundayAt"
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

$description = @"
Weekly DNS/deploy axis isolation: mkmlife CF Workers vs jema-ai/logos VPS canonical split.
[HYPO] B-track — probe only; no mkmlife deploy. SSOT: probe_mkm_deployment_axis_isolation_v1.py
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: powershell -File scripts\Verify-MkmDeploymentAxisIsolationWeeklyScheduledTask_v1.ps1"
Write-Host "Manual: powershell -File scripts\Invoke-MkmDeploymentAxisIsolationWeeklyRoutine_v1.ps1"
