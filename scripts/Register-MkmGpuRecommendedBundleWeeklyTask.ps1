<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task for the GPU-adjacent recommended bundle (Control-Integrity oracle + Pack 0-B pytest).

.DESCRIPTION
  Runs: scripts/Run-MkmGpuRecommendedBundle_v1.ps1
  Default: Sunday 08:00 local (after MKM_Compression_WeeklyGovernance 07:00 if both registered).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_GpuRecommendedBundle_Weekly).

.PARAMETER SundayAt
  Local time HH:mm for weekly Sunday trigger (default: 08:00).

.PARAMETER SkipControlIntegrity
  Pass -SkipControlIntegrity to the runner (Pack 0-B pytest only).

.PARAMETER SkipPack0B
  Pass -SkipPack0B to the runner (oracle chain only).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_GpuRecommendedBundle_Weekly",
    [string]$SundayAt = "08:00",
    [switch]$SkipControlIntegrity,
    [switch]$SkipPack0B,
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

$runner = Join-Path $resolvedRoot "scripts\Run-MkmGpuRecommendedBundle_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 08:00), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($SkipControlIntegrity) { $argLine += " -SkipControlIntegrity" }
if ($SkipPack0B) { $argLine += " -SkipPack0B" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $resolvedRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly: Run-MkmGpuRecommendedBundle_v1 (Control-Integrity oracle chain + Pack 0-B pytest slice). Workspace: $resolvedRoot"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
if ($SkipControlIntegrity) { Write-Host "Note: task passes -SkipControlIntegrity." }
if ($SkipPack0B) { Write-Host "Note: task passes -SkipPack0B." }
