#Requires -Version 5.1
<#
.SYNOPSIS
  Register logoff trigger: safe vscdb janitor when Cursor session ends.

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_CursorStateVscdbJanitor_OnLogoff"
)

$ErrorActionPreference = "Stop"
$janitor = Join-Path $WorkspaceRoot "scripts\Invoke-CursorStateVscdbJanitor_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\cursor_state_vscdb_janitor_on_logoff.log"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $janitor)) {
    throw "Missing: $janitor"
}

$psArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$janitor`" -Apply"
$taskRun = "cmd.exe /c cd /d `"$WorkspaceRoot`" && powershell.exe $psArgs >> `"$log`" 2>&1"
$eventQuery = "*[System[Provider[@Name='Microsoft-Windows-Winlogon'] and (EventID=7002)]]"
schtasks /Create /TN $TaskName /TR $taskRun /SC ONEVENT /EC System /MO $eventQuery /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks register failed exit=$LASTEXITCODE"
}

Write-Host "Registered: $TaskName (Winlogon 7002 logoff -> janitor -Apply)"
Write-Host "  Log: $log"
