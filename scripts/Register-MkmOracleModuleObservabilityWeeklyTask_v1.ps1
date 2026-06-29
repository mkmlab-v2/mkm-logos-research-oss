<#
.SYNOPSIS
  Register weekly Scheduled Task: Oracle module observability (narrative/closure + resume pack).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_Oracle_Module_Observability_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default: 09:45 — after HD AE 09:15).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Oracle_Module_Observability_Weekly",
    [string]$SundayAt = "09:45"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
$runner = Join-Path $workspaceRoot "scripts\Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 09:45), got: $SundayAt"
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
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = @"
Weekly Oracle module lane: narrative/closure observability + logos overlay + oracle resume pack.
[HYPO] tier_0 — no bloom cap bump / no mkmlife deploy. SSOT: .cursor/rules/logos-oracle-module-tier2-prep-v1.mdc
"@.Trim()

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Verify: powershell -File scripts\Verify-MkmOracleModuleObservabilityWeeklyScheduledTask_v1.ps1"
Write-Host "Manual: powershell -File scripts\Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1"
