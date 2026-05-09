param(
    [string]$TaskName = "MKM-Logos-PureReal-WeeklySnapshot"
)

$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

$out = [pscustomobject]@{
    ok = $true
    task_name = $task.TaskName
    task_path = $task.TaskPath
    state = [string]$task.State
    next_run_time = $info.NextRunTime
    last_run_time = $info.LastRunTime
    last_task_result = $info.LastTaskResult
    execute = $task.Actions.Execute
    arguments = $task.Actions.Arguments
    working_directory = $task.Actions.WorkingDirectory
}

$out | ConvertTo-Json -Compress

