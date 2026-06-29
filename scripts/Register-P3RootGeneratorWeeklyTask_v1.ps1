<#
.SYNOPSIS
  Register weekly Scheduled Task for P3 Root Generator ops (B-track).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_P3RootGenerator_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default: 09:45 — after DR bench 09:30).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_P3RootGenerator_Weekly",
    [string]$SundayAt = "09:45",
    [switch]$OfflineShallow,
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

$runner = Join-Path $resolvedRoot "scripts\Invoke-P3RootGeneratorWeekly_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$offlineFlag = if ($OfflineShallow) { " -OfflineShallow" } else { "" }
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"$offlineFlag"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $resolvedRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$mode = if ($OfflineShallow) { "offline shallow skip" } else { "live shallow slice if Ollama up" }
$description = "Weekly: P3 Root Generator extension+replacement research. Mode: $mode. B-track HOLD."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt)"
Write-Host "Runner: $runner"
Write-Host "Track: B-track research_only send_gate HOLD"
