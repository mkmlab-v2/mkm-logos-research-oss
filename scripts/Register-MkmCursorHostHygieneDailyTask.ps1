#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily Cursor host hygiene (vscdb watch + safe janitor).

.DESCRIPTION
  Single task replacing ad-hoc disabled cursor weekly duplicates for host SSOT.
  Runs hygiene check then janitor -Apply when Cursor is not running.

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_CursorHostHygiene_Daily",
    [string]$AtLocalTime = "08:45"
)

$ErrorActionPreference = "Stop"

$hygiene = Join-Path $WorkspaceRoot "scripts\check_cursor_state_vscdb_hygiene_v1.ps1"
$janitor = Join-Path $WorkspaceRoot "scripts\Invoke-CursorStateVscdbJanitor_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\cursor_host_hygiene_daily.log"

if (-not (Test-Path -LiteralPath $hygiene)) {
    throw "Missing: $hygiene"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = @(
    "/c cd /d `"$WorkspaceRoot`" &&",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$hygiene`" -WorkspaceRoot `"$WorkspaceRoot`" >> `"$log`" 2>&1 &&",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$janitor`" -WorkspaceRoot `"$WorkspaceRoot`" -Apply >> `"$log`" 2>&1"
) -join " "

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Daily at $AtLocalTime (local)"
Write-Host "  Log: $log"
Write-Host "  Chain: hygiene -> janitor -Apply (skip delete when Cursor running)"
