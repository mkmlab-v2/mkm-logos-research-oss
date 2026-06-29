<#
.SYNOPSIS
  Register (or remove) weekly Scheduled Task for MKM deep research DR bench mini (P2-G).

.DESCRIPTION
  Runs: powershell -File scripts\Invoke-MkmDeepResearchBenchWeekly_v1.ps1
  Default: Sunday 09:30 local (after compression governance 07:00).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_DeepResearch_Bench_Weekly).

.PARAMETER SundayAt
  Local time HH:mm (default: 09:30).

.PARAMETER OfflineOnly
  Register task with -OfflineOnly (pytest smoke only, no arXiv network).

.PARAMETER AllowFallback
  Register task with -AllowFallback (disable strict --require-entry-level).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_DeepResearch_Bench_Weekly",
    [string]$SundayAt = "09:30",
    [switch]$OfflineOnly,
    [switch]$AllowFallback,
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

$runner = Join-Path $resolvedRoot "scripts\Invoke-MkmDeepResearchBenchWeekly_v1.ps1"

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
    throw "SundayAt must be HH:mm (e.g. 09:30), got: $SundayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$offlineFlag = if ($OfflineOnly) { " -OfflineOnly" } else { "" }
$fallbackFlag = if ($AllowFallback) { " -AllowFallback" } else { "" }
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`"$offlineFlag$fallbackFlag"

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

$mode = if ($OfflineOnly) { "offline pytest only" } elseif ($AllowFallback) { "pytest + online DR bench mini (fallback allowed)" } else { "pytest + online DR bench mini (strict entry-level)" }
$description = "Weekly: MKM deep research DR bench mini (P2-G). Mode: $mode. Workspace: $resolvedRoot"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Sunday $SundayAt, user=$env:USERNAME)"
Write-Host "SSOT tier: tier3_optional_active (mkm_scheduler_solo_core_stack_v1.json)"
Write-Host "Runner: $runner"
Write-Host "Track: B-track research_only send_gate HOLD"
