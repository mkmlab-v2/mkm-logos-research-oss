#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_CommanderInterestBenchmark_Weekly scheduled task.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_CommanderInterestBenchmark_Weekly"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$argStr = [string]$a.Arguments

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("arguments={0}" -f $argStr)
$hasChain = $argStr -match 'Run-CommanderInterestBenchmarkChain_v1\.ps1'
Write-Output ("commander_interest_benchmark_chain_in_task_action={0}" -f $hasChain)
