#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM-LogosThemeRunContinuous scheduled task and last integrate state.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-LogosThemeRunContinuous",
    [string]$WorkspaceRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Output "scheduled_task_exists=false"
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Output "scheduled_task_exists=true"
Write-Output ("state={0}" -f $task.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("next_run_time={0}" -f $info.NextRunTime)

$stopFile = Join-Path $repoRoot "docs\research\logos_metaphor_db_v1\LOGOS_THEME_RUN.stop"
Write-Output ("stop_file_present={0}" -f (Test-Path -LiteralPath $stopFile))

$statePath = Join-Path $repoRoot "reports\logos_theme_run_state_v1_latest.json"
if (Test-Path -LiteralPath $statePath) {
    Write-Output "state_json=$statePath"
    Get-Content -LiteralPath $statePath -Raw | Write-Output
} else {
    Write-Output "state_json=missing"
}

exit 0
