#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: MKM Bounded Lane Loop all-lanes operational (shadow only).

.DESCRIPTION
  Runs Invoke-BoundedLaneLoopAllLanes_v1.ps1 with -RefreshPin + meta envelope fixture.
  Shadow mechanical runner — no Track A promotion · no todo_queue enqueue.
  Complements MKM_BoundedLaneLoop_Shadow_Weekly (dry-run pytest persona) at 09:30.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_BoundedLaneLoop_AllLanes_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default 10:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BoundedLaneLoop_AllLanes_Weekly",
    [string]$SundayAt = "10:00",
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

$runner = Join-Path $resolvedRoot "scripts\Invoke-BoundedLaneLoopAllLanes_v1.ps1"
$envelope = Join-Path $resolvedRoot "docs\final\artifacts\fixtures\mkm_meta_layer_turn_envelope_v1.example.json"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing: $runner"
}
if (-not (Test-Path -LiteralPath $envelope)) {
    throw "Missing meta envelope fixture: $envelope"
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

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -RefreshPin -MetaLayerEnvelopePath `"$envelope`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly External Cortex 4-lane bounded loop (ms/oracle/infra/design). SSOT: Invoke-BoundedLaneLoopAllLanes_v1.ps1"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (Sunday $SundayAt)"
Write-Host "Runner: $runner -RefreshPin -MetaLayerEnvelopePath ..."
exit 0
