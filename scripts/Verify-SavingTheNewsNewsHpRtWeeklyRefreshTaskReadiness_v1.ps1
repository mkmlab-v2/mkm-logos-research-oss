param(
    [string]$TaskName = "MKM_SavingTheNews_NewsHpRt_WeeklyRefresh"
)

$ErrorActionPreference = "Stop"
$shortName = $TaskName.TrimStart("\")
$t = Get-ScheduledTask -TaskName $shortName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]

Write-Output "task_name=$shortName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $a.Arguments)
Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
