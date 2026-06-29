#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Agent Handoff Governance baseline chain (ops_memory + phase1 pack + JSONL).

.DESCRIPTION
  Runs: scripts\Invoke-AgentHandoffGovernanceWeeklyBaseline_v1.ps1
  Default: Sunday 07:15 local (after MKM_Workspace_Lifecycle_Weekly ~06:30).

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_AgentHandoffGovernance_WeeklyBaseline",
    [string]$SundayAt = "07:15",
    [switch]$RunWhenLoggedOff
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Invoke-AgentHandoffGovernanceWeeklyBaseline_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 07:15), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$logonType = if ($RunWhenLoggedOff) { "S4U" } else { "Interactive" }
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType $logonType -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Registered: $TaskName (Sunday $SundayAt, logon=$logonType)"
Write-Host "Runner: $runner"
exit 0
