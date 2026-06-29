#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_ParallelPassiveLoop_Daily scheduled task and runner paths.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_ParallelPassiveLoop_Daily"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-ParallelPassiveLoop_v1.ps1"
$pyRunner = Join-Path $WorkspaceRoot "scripts\run_parallel_passive_loop_v1.py"

$ok = $true
if (-not (Test-Path -LiteralPath $runner)) {
    Write-Host "FAIL missing $runner" -ForegroundColor Red
    $ok = $false
}
if (-not (Test-Path -LiteralPath $pyRunner)) {
    Write-Host "FAIL missing $pyRunner" -ForegroundColor Red
    $ok = $false
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "WARN task not registered: $TaskName" -ForegroundColor Yellow
    $ok = $false
} else {
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Host "task_state=$($task.State) last_result=$($info.LastTaskResult) next_run=$($info.NextRunTime)"
    $action = ($task.Actions | Select-Object -First 1).Arguments
    if ($action -notmatch "Invoke-ParallelPassiveLoop_v1\.ps1") {
        Write-Host "FAIL unexpected task action" -ForegroundColor Red
        $ok = $false
    }
    if ($action -match "IncludeWebOps") {
        Write-Host "FAIL task must not include Nebius/web_ops" -ForegroundColor Red
        $ok = $false
    }
}

if ($ok) { exit 0 }
exit 1
