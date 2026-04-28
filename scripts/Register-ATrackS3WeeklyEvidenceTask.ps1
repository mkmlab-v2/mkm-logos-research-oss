<#
.SYNOPSIS
  Register (or remove) a weekly Scheduled Task for Track A S3 evidence rollup + checklist/go-nogo alignment.

.DESCRIPTION
  Runs: py scripts/run_a_track_s3_weekly_evidence_rollup_v1.py --emit-missing-governance
  Requires: Python launcher `py`, repo at C:\workspace (override with -WorkspaceRoot).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_ATrack_S3WeeklyRollup).

.PARAMETER WeeklyAt
  Local time HH:mm for weekly trigger (default: 06:05 Monday).

.PARAMETER WorkspaceRoot
  Repository root containing scripts\ (default: C:\workspace).

.PARAMETER SkipEmitGovernance
  If set, omit --emit-missing-governance (only use if governance JSON is always managed manually).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_ATrack_S3WeeklyRollup",
    [string]$WeeklyAt = "06:05",
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipEmitGovernance
)

$ErrorActionPreference = "Stop"

$rollup = Join-Path $WorkspaceRoot "scripts\run_a_track_s3_weekly_evidence_rollup_v1.py"
if (-not (Test-Path -LiteralPath $rollup)) {
    throw "Rollup script not found: $rollup"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) {
    throw "WeeklyAt must be HH:mm (e.g. 06:05), got: $WeeklyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$pyTail = if ($SkipEmitGovernance) { "" } else { " --emit-missing-governance" }

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Set-Location -LiteralPath '$WorkspaceRoot'; py -3 `"$rollup`"$pyTail`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Track A: multiweek tracker increment + hold checklist + go/nogo refresh. Uses emit-missing-governance unless -SkipEmitGovernance at registration time."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (weekly Monday $WeeklyAt, user=$env:USERNAME)"
Write-Host "Workspace: $WorkspaceRoot"
Write-Host "Emit governance: $(-not $SkipEmitGovernance)"
