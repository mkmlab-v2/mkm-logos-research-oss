<#
.SYNOPSIS
  Register logon Scheduled Task: Cursor IDE Browser warmup (no Reload).

.DESCRIPTION
  Runs Invoke-CursorIdeBrowserWarmup_v1.ps1 when user logs on.
  Keeps Browser Tab + diet settings warm; NEW Agent chat still required for browser_* per chat.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_CursorIdeBrowserWarmup_Logon
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CursorIdeBrowserWarmup_Logon",
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if ($WorkspaceRoot -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
} elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$warmup = Join-Path $resolvedRoot "scripts\Invoke-CursorIdeBrowserWarmup_v1.ps1"
if (-not (Test-Path -LiteralPath $warmup)) {
    throw "Missing: $warmup"
}

$argLine = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$warmup`" -WorkspaceRoot `"$resolvedRoot`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Registered: $TaskName (AtLogOn -> Invoke-CursorIdeBrowserWarmup_v1.ps1)"
Write-Host "Verify: Get-ScheduledTask -TaskName $TaskName"
exit 0
