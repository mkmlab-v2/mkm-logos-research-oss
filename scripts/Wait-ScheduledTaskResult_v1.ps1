param(
    [string]$TaskName,
    [int]$TimeoutSec = 180
)
$deadline = (Get-Date).AddSeconds($TimeoutSec)
do {
    Start-Sleep -Seconds 3
    $state = (Get-ScheduledTask -TaskName $TaskName).State
} while ($state -eq 'Running' -and (Get-Date) -lt $deadline)
$info = Get-ScheduledTaskInfo -TaskName $TaskName
[pscustomobject]@{
    TaskName     = $TaskName
    State        = $state
    LastResult   = $info.LastTaskResult
    LastRunTime  = $info.LastRunTime
}
exit [int]$info.LastTaskResult
