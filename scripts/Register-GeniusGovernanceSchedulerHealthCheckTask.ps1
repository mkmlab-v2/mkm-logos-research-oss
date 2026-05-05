<#
.SYNOPSIS
  Register (or remove) periodic genius governance scheduler health check task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_GeniusGovernance_SchedulerHealthCheck",
    [string]$StartAt = "00:00",
    [int]$RepeatMinutes = 60
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_genius_governance_scheduler_health_cycle_v1.ps1"
$outJson = Join-Path $workspaceRoot "docs\final\artifacts\genius_governance_scheduler_health_check_latest.json"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($RepeatMinutes -lt 30) {
    throw "RepeatMinutes must be >= 30 for stable monitoring."
}

$parts = $StartAt -split ':'
if ($parts.Count -lt 2) { throw "StartAt must be HH:mm, got: $StartAt" }

$taskRun = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""

$createArgs = @(
    "/Create",
    "/F",
    "/TN", $TaskName,
    "/SC", "DAILY",
    "/ST", $StartAt,
    "/RI", "$RepeatMinutes",
    "/DU", "24:00",
    "/TR", $taskRun
)
& schtasks.exe @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to register health check task via schtasks.exe" }

# Keep task silent and avoid overlap.
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew
Set-ScheduledTask -TaskName $TaskName -Settings $settings | Out-Null

Write-Host "Registered scheduled task: $TaskName (every $RepeatMinutes min, user=$env:USERNAME)"
Write-Host "Runner: $runner"
