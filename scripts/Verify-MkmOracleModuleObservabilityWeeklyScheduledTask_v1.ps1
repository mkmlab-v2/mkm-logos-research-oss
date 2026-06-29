#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_Oracle_Module_Observability_Weekly scheduled task.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_Oracle_Module_Observability_Weekly",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
if (-not $OutJson) {
    $OutJson = Join-Path $root "reports\mkm_oracle_module_observability_weekly_scheduled_ops_readiness_v1_latest.json"
}

$runnerExpected = Join-Path $root "scripts\Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1.ps1"

$payload = [ordered]@{
    schema                         = "mkm_oracle_module_observability_weekly_scheduled_ops_readiness_v1"
    generated_at_utc               = (Get-Date).ToUniversalTime().ToString("o")
    task_name                      = $TaskName
    task_exists                    = $false
    state                          = $null
    runner_exists                  = (Test-Path -LiteralPath $runnerExpected)
    arguments_contain_weekly_routine = $false
    research_only                  = $true
    ready                          = $false
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
    $payload.task_exists = $true
    $payload.state = [string]$task.State
    $argStr = [string]$task.Actions[0].Arguments
    if ($argStr -match 'Invoke-MkmOracleModuleObservabilityWeeklyRoutine_v1\.ps1') {
        $payload.arguments_contain_weekly_routine = $true
    }
}

$payload.ready = $payload.runner_exists -and (
    (-not $payload.task_exists) -or $payload.arguments_contain_weekly_routine
)

$payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutJson -Encoding utf8
Write-Output ("ready={0} task_exists={1} runner_exists={2}" -f $payload.ready, $payload.task_exists, $payload.runner_exists)
if (-not $payload.runner_exists) { exit 1 }
exit 0
