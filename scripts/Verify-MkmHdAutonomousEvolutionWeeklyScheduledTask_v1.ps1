#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_HdAutonomousEvolution_Weekly scheduled task (JSON + optional file out).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_HdAutonomousEvolution_Weekly",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
if (-not $OutJson) {
    $OutJson = Join-Path $root "reports\hd_autonomous_evolution_scheduled_ops_readiness_v1_latest.json"
}

$runnerExpected = Join-Path $root "scripts\Invoke-MkmHdAutonomousEvolutionWeeklyRoutine_v1.ps1"
$orchestratorExpected = Join-Path $root "scripts\Invoke-MkmHighDimensionalAutonomousEvolution_v1.ps1"

$payload = [ordered]@{
    schema                    = "hd_autonomous_evolution_scheduled_ops_readiness_v1"
    generated_at_utc          = (Get-Date).ToUniversalTime().ToString("o")
    task_name                 = $TaskName
    task_exists               = $false
    state                     = $null
    last_task_result          = $null
    next_run_time             = $null
    runner_path               = $runnerExpected.Replace('\', '/')
    runner_exists             = (Test-Path -LiteralPath $runnerExpected)
    orchestrator_exists       = (Test-Path -LiteralPath $orchestratorExpected)
    arguments_contain_weekly_routine = $false
    arguments_contain_hybrid  = $false
    research_only             = $true
    hypothesis_tag            = "[HYPO]"
    ready                     = $false
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
    $payload.task_exists = $true
    $payload.state = [string]$task.State
    $info = Get-ScheduledTaskInfo -InputObject $task
    $payload.last_task_result = $info.LastTaskResult
    $payload.next_run_time = if ($info.NextRunTime) { $info.NextRunTime.ToUniversalTime().ToString("o") } else { $null }
    $argStr = [string]$task.Actions[0].Arguments
    if ($argStr -match 'Invoke-MkmHdAutonomousEvolutionWeeklyRoutine_v1\.ps1') {
        $payload.arguments_contain_weekly_routine = $true
    }
    if ($argStr -match 'IncludeP0P1P2Hybrid') {
        $payload.arguments_contain_hybrid = $true
    }
}

$payload.ready = (
    $payload.runner_exists -and
    $payload.orchestrator_exists -and
    $payload.task_exists -and
    $payload.state -eq 'Ready' -and
    $payload.arguments_contain_weekly_routine
)

$json = $payload | ConvertTo-Json -Depth 6
$OutJson | Split-Path -Parent | ForEach-Object { if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null } }
Set-Content -LiteralPath $OutJson -Value $json -Encoding utf8

Write-Host $json
if (-not $payload.ready) { exit 1 }
exit 0
