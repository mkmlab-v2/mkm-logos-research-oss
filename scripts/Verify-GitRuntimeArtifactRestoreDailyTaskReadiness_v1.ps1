#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_GitRuntimeArtifactRestore_Daily scheduled task registration.
#>
param(
    [string]$TaskName = "MKM_GitRuntimeArtifactRestore_Daily",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-GitRuntimeArtifactRestore_v1.ps1"
$ok = $true

if (-not (Test-Path -LiteralPath $runner)) {
    Write-Host "FAIL: missing runner $runner" -ForegroundColor Red
    exit 1
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "FAIL: scheduled task not registered: $TaskName" -ForegroundColor Red
    Write-Host "Fix: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-GitRuntimeArtifactRestoreDailyTask.ps1"
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
$action = $task.Actions | Select-Object -First 1
Write-Host "OK: $TaskName"
Write-Host "  State: $($task.State)"
Write-Host "  NextRunTime: $($info.NextRunTime)"
Write-Host "  Action: $($action.Execute) $($action.Arguments)"
exit 0
