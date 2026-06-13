<#
.SYNOPSIS
  Fact-Lock spot check for A2A scheduled tasks (daily dogfood + weekly repro).

.EXAMPLE
  powershell -File scripts\Verify-A2aScheduledTasksReadiness_v1.ps1
#>
[CmdletBinding()]
param(
    [string[]]$TaskNames = @(
        "MKM_A2A_Dogfood_Passive_Daily",
        "MKM_A2A_Weekly_Repro_Bundle"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$allOk = $true
foreach ($TaskName in $TaskNames) {
    Write-Host "== $TaskName ==" -ForegroundColor Cyan
    try {
        $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -InputObject $t
        $a = $t.Actions[0]
        Write-Output "task_name=$TaskName"
        Write-Output ("state={0}" -f $t.State)
        Write-Output ("last_run_time={0}" -f $info.LastRunTime)
        Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
        Write-Output ("next_run_time={0}" -f $info.NextRunTime)
        Write-Output ("execute={0}" -f $a.Execute)
        Write-Output ("arguments={0}" -f $a.Arguments)
        Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
        if ($t.State -ne "Ready") {
            $allOk = $false
            Write-Warning "task_not_ready: $TaskName state=$($t.State)"
        }
    }
    catch {
        $allOk = $false
        Write-Warning "task_missing: $TaskName — $($_.Exception.Message)"
    }
    Write-Host ""
}

if (-not $allOk) {
    Write-Host "A2A_SCHEDULED_TASKS_READY=False" -ForegroundColor Red
    exit 1
}

Write-Host "A2A_SCHEDULED_TASKS_READY=True" -ForegroundColor Green
exit 0
