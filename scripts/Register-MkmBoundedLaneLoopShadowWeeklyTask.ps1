#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: MKM Bounded Lane Loop Shadow (External Cortex passive gate).

.DESCRIPTION
  Runs Invoke-MkmPersonaHealth_v1.ps1 -Persona BoundedLaneLoopShadow (P0 + pytest + dry-run invoke).
  Shadow only — no Track A promotion · no todo_queue enqueue.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_BoundedLaneLoop_Shadow_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default 09:30).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BoundedLaneLoop_Shadow_Weekly",
    [string]$SundayAt = "09:30",
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$runner = Join-Path $resolvedRoot "scripts\Invoke-MkmPersonaHealth_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing -and $existing.State -in @('Ready', 'Running')) {
    Write-Host "Already registered ($($existing.State)): $TaskName"
    exit 0
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) { throw "SundayAt must be HH:mm, got: $SundayAt" }
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Persona BoundedLaneLoopShadow"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly External Cortex bounded lane shadow gate. SSOT: Invoke-MkmPersonaHealth_v1.ps1 -Persona BoundedLaneLoopShadow"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (Sunday $SundayAt)"
Write-Host "Runner: $runner -Persona BoundedLaneLoopShadow"
exit 0
