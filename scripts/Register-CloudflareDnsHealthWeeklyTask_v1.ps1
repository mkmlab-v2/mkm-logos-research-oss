#Requires -Version 5.1
<#
.SYNOPSIS
  Register a weekly scheduled task: Cloudflare DNS token verify + ensure chain + HTTPS HEAD (jemaai.cloud).

.PARAMETER Remove
  Unregister the task.

.PARAMETER DryRun
  Print actions only; do not register.

.PARAMETER WorkspaceRoot
  Repo root (default C:\workspace).

.PARAMETER TaskName
  Scheduled task name (default MKM_CloudflareDnsHealthWeekly).

.NOTES
  Chain runs without -AllowDeleteConflictingWwwHost by default (non-destructive). Edit Invoke-CloudflareDnsHealthCheck_v1.ps1 flags if you need maintenance mode.
#>
param(
    [switch]$Remove,
    [switch]$DryRun,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_CloudflareDnsHealthWeekly",
    [System.DayOfWeek]$DayOfWeek = [System.DayOfWeek]::Monday,
    [string]$AtLocalTime = "08:15"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-CloudflareDnsHealthCheck_v1.ps1"
if (-not $Remove -and -not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`""
if ($DryRun) {
    Write-Host "[DryRun] Would register: $TaskName"
    Write-Host "  Weekly: $DayOfWeek at $AtLocalTime (local)"
    Write-Host "  Runner: $runner"
    Write-Host "  ArgLine: $argLine"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Weekly: $DayOfWeek at $AtLocalTime (local)"
Write-Host "  Runner: $runner"
Write-Host ""
Write-Host "Manual run:" -ForegroundColor Cyan
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
