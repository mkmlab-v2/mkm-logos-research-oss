#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly MKM workspace lifecycle audit (Sunday 06:30 local).
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$taskName = "MKM_Workspace_Lifecycle_Weekly"
$scriptPath = Join-Path $WorkspaceRoot "scripts\Invoke-MkmWorkspaceLifecycleRoutine_v1.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "06:30"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task $taskName"
    exit 0
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Registered $taskName -> $scriptPath (Sunday 06:30)"
exit 0
