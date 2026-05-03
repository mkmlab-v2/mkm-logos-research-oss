<#

.SYNOPSIS

  Optional Track C queue refresh from bridge, then one MKM-Orchestrator poll.



.DESCRIPTION

  Default: poll only. Use -RefreshQueue when mkm_trackc_plan_orchestrator_bridge_v1.json changed

  (rebuilds todo_queue_latest.json; overwrites queue state).

  Periodic poll: Register-MkmOrchestratorPollTask.ps1. Weekly bundle+pytest: Register-TrackCPlanGatesSmokeTask.ps1.

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [switch]$RefreshQueue,

    [switch]$RefreshQueueDryRun,

    [switch]$SkipPoll,

    [int]$MaxTasksPerInvocation = 1,

    [switch]$PollDryRun,

    [switch]$SkipLock

)



$ErrorActionPreference = "Stop"



$refresh = Join-Path $WorkspaceRoot "scripts\Invoke-TrackCPlanQueueRefresh.ps1"

if (-not (Test-Path -LiteralPath $refresh)) { throw "Not found: $refresh" }



if ($RefreshQueueDryRun) {

    & $refresh -WorkspaceRoot $WorkspaceRoot -DryRun

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

} elseif ($RefreshQueue) {

    & $refresh -WorkspaceRoot $WorkspaceRoot

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

}



if ($SkipPoll) {

    exit 0

}



$poll = Join-Path $WorkspaceRoot "scripts\mkm_orchestrator_poll.ps1"

if (-not (Test-Path -LiteralPath $poll)) { throw "Not found: $poll" }



$pArgs = @{ WorkspaceRoot = $WorkspaceRoot; MaxTasksPerInvocation = $MaxTasksPerInvocation }

if ($PollDryRun) { $pArgs.DryRun = $true }

if ($SkipLock) { $pArgs.SkipLock = $true }

& $poll @pArgs

exit $LASTEXITCODE

