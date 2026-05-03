<#
.SYNOPSIS
  Quick heartbeat proof for MKM daemon loop.

.DESCRIPTION
  Shows daemon task state and recent audit timestamps/events so operators can
  verify background loop activity without scanning full logs.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_OrchestratorDaemon",
    [int]$Tail = 8
)

$ErrorActionPreference = "Stop"
if ($Tail -lt 1) { throw "Tail must be >= 1" }

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "daemon_task_missing: $TaskName"
    exit 1
}

$info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
Write-Host ("daemon_state={0}" -f $task.State)
if ($null -ne $info) {
    Write-Host ("last_run={0}" -f $info.LastRunTime)
    Write-Host ("last_result={0}" -f $info.LastTaskResult)
}

$audit = Join-Path $WorkspaceRoot "reports\mkm_orchestrator_audit.jsonl"
if (-not (Test-Path -LiteralPath $audit)) {
    Write-Host "audit_missing: $audit"
    exit 0
}

Write-Host "--- recent_audit ---"
Get-Content -LiteralPath $audit -Tail $Tail | ForEach-Object {
    try {
        $row = $_ | ConvertFrom-Json
        $tid = if ($row.task_id) { " task_id=$($row.task_id)" } else { "" }
        Write-Host ("{0} {1}{2}" -f $row.ts_utc, $row.event, $tid)
    } catch {
        Write-Host $_
    }
}
