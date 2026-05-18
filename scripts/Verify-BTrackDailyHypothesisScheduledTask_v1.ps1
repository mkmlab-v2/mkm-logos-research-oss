#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM-BTrack-DailyHypothesis-Chain scheduled task registration (JSON stdout).

.DESCRIPTION
  Reads Task Scheduler action arguments and reports Phase3 / research-instrument flags.
  Missing task is not a failure (exit 0, task_exists=false).

.NOTES
  Re-register with scripts/Register-BTrackDailyHypothesisTask.ps1 (same -TaskName overwrites).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-BTrack-DailyHypothesis-Chain"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-MissingTaskPayload {
    return [pscustomobject]@{
        task_exists                                      = $false
        arguments_contain_include_phase3_leading_sensors = $false
        arguments_contain_skip_phase3_network_fetch      = $false
        research_evaluation_instrument                   = $null
        next_run_time                                    = $null
    }
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    (New-MissingTaskPayload) | ConvertTo-Json -Compress
    exit 0
}

$info = Get-ScheduledTaskInfo -InputObject $task
$argStr = [string]$task.Actions[0].Arguments

$includePhase3 = $false
if ($argStr -match '(^|\s)-IncludePhase3LeadingSensors(\s|$)') { $includePhase3 = $true }

$skipPhase3Fetch = $false
if ($argStr -match '(^|\s)-SkipPhase3NetworkFetch(\s|$)') { $skipPhase3Fetch = $true }

$instrument = $null
if ($argStr -match '(^|\s)-ResearchEvaluationInstrument\s+(btc|kospi|multi)(\s|$)') {
    $instrument = $Matches[2]
}

$nextRun = $null
if ($info.NextRunTime -and $info.NextRunTime.Year -gt 2000) {
    $nextRun = $info.NextRunTime.ToString("o")
}

$out = [pscustomobject]@{
    task_exists                                      = $true
    arguments_contain_include_phase3_leading_sensors = $includePhase3
    arguments_contain_skip_phase3_network_fetch      = $skipPhase3Fetch
    research_evaluation_instrument                   = $instrument
    next_run_time                                    = $nextRun
}

$out | ConvertTo-Json -Compress
exit 0
