#Requires -Version 5.1
<#
.SYNOPSIS
  Register daily git runtime artifact restore (Cursor Git UI hygiene).

.DESCRIPTION
  Default: daily 07:45 local — before MKM_McpHygieneProbe_Daily (08:30).

.PARAMETER Remove
  Unregister the task.
#>
param(
    [switch]$Remove,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_GitRuntimeArtifactRestore_Daily",
    [string]$AtLocalTime = "07:45"
)

$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Invoke-GitRuntimeArtifactRestore_v1.ps1"
$outJson = Join-Path $WorkspaceRoot "reports\git_runtime_artifact_restore_latest.json"
$log = Join-Path $WorkspaceRoot "reports\git_runtime_artifact_restore_daily.log"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

$cmdArgs = "/c cd /d `"$WorkspaceRoot`" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -OutJson `"$outJson`" >> `"$log`" 2>&1"

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgs
$trigger = New-ScheduledTaskTrigger -Daily -At $AtLocalTime
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null

Write-Host "Registered: $TaskName" -ForegroundColor Green
Write-Host "  Daily at $AtLocalTime (local)"
Write-Host "  JSON: $outJson"
Write-Host "  Log : $log"
