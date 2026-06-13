<#
.SYNOPSIS
  Register (or remove) weekly Scheduled Task for RQ-019 inter-agent quick smoke.

.DESCRIPTION
  Runs: scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1
  Default: Sunday 08:30 local (after GpuRecommendedBundle 08:00 if both registered).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_InterAgent_RQ019_Weekly_Smoke).

.PARAMETER SundayAt
  Local time HH:mm for weekly Sunday trigger (default: 08:30).

.PARAMETER SkipEncodingStatus
  Pass -SkipEncodingStatus to the runner.

.PARAMETER IncludeA2aExtendedRepro
  Pass -IncludeA2aExtendedRepro to the runner (L1L2 chain + tp01 log + stack map; skips dialogue bench).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_InterAgent_RQ019_Weekly_Smoke",
    [string]$SundayAt = "08:30",
    [switch]$SkipEncodingStatus,
    [switch]$IncludeA2aExtendedRepro,
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

$runner = Join-Path $resolvedRoot "scripts\Run-MkmInterAgentRq019WeeklySmoke_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 08:30), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($SkipEncodingStatus) { $argLine += " -SkipEncodingStatus" }
if ($IncludeA2aExtendedRepro) { $argLine += " -IncludeA2aExtendedRepro" }

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

$description = "Weekly: RQ-019 inter-agent quick smoke (B-track research_only). Workspace: $resolvedRoot"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
