#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily scheduled task: Invoke-SafeOpsSurfaceCheck.ps1 (reports/safe_ops_surface_check_latest.json).

.PARAMETER Remove
  Unregister the task.

.PARAMETER IncludeVpsSmoke
  Pass through to Invoke-SafeOpsSurfaceCheck (SSH smoke; slower).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-SafeOpsSurfaceCheckTask.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-SafeOpsSurfaceCheckTask.ps1 -AtLocalTime "09:15"
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-SafeOpsSurfaceCheckTask.ps1 -IncludeVpsSmoke
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_SafeOpsSurfaceCheck_Daily",
    [string]$AtLocalTime = "09:15",
    [switch]$IncludeVpsSmoke
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-SafeOpsSurfaceCheck.ps1"
$log = Join-Path $WorkspaceRoot "reports\safe_ops_surface_check_daily.log"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Script missing: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$smokeArg = if ($IncludeVpsSmoke) { " -IncludeVpsSmoke" } else { "" }
$cmdArgs = "/c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`"$smokeArg >> `"$log`" 2>&1"

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Daily at $AtLocalTime (local)"
Write-Host "  Runner: $runner"
Write-Host "  Log   : $log"
Write-Host "  IncludeVpsSmoke: $IncludeVpsSmoke"
