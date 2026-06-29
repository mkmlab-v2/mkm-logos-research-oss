#Requires -Version 5.1
<#
.SYNOPSIS
  Register MKM host resource guard (4x daily, auto-remediate Ollama on pressure).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MkmHostResourceGuardTask_v1.ps1
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-MkmHostResourceGuardTask_v1.ps1 -Remove
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_HostResourceGuard_4xDaily"
)

$ErrorActionPreference = "Stop"

$guard = Join-Path $WorkspaceRoot "scripts\Invoke-MkmHostResourceGuard_v1.ps1"
$log = Join-Path $WorkspaceRoot "reports\mkm_host_resource_guard_daily.log"

if (-not (Test-Path -LiteralPath $guard)) {
    throw "Missing: $guard"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = @(
    "/c cd /d `"$WorkspaceRoot`" &&",
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$guard`" -WorkspaceRoot `"$WorkspaceRoot`" -Apply >> `"$log`" 2>&1"
) -join " "

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At "08:15"),
    (New-ScheduledTaskTrigger -Daily -At "12:30"),
    (New-ScheduledTaskTrigger -Daily -At "17:00"),
    (New-ScheduledTaskTrigger -Daily -At "22:30")
)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Times (local): 08:15, 12:30, 17:00, 22:30"
Write-Host "  Log: $log"
Write-Host "  Chain: Invoke-MkmHostResourceGuard_v1.ps1 -Apply"
