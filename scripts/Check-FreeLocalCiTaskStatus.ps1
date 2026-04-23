<#
.SYNOPSIS
  Print status summary for free local CI scheduled tasks.

.DESCRIPTION
  Shows State/LastRunTime/LastTaskResult/NextRunTime for:
  - MKM_FreeLocalCI_Daily
  - MKM_FreeLocalCI_WeeklyFull
#>

$ErrorActionPreference = "Stop"

$taskNames = @(
    "MKM_FreeLocalCI_Daily",
    "MKM_FreeLocalCI_WeeklyFull"
)

$rows = foreach ($name in $taskNames) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if (-not $task) {
        [pscustomobject]@{
            TaskName      = $name
            State         = "NOT_FOUND"
            LastRunTime   = $null
            LastTaskResult = $null
            NextRunTime   = $null
        }
        continue
    }

    $info = Get-ScheduledTaskInfo -TaskName $name -ErrorAction SilentlyContinue
    [pscustomobject]@{
        TaskName       = $name
        State          = $task.State
        LastRunTime    = $info.LastRunTime
        LastTaskResult = $info.LastTaskResult
        NextRunTime    = $info.NextRunTime
    }
}

$rows | Format-Table -AutoSize
