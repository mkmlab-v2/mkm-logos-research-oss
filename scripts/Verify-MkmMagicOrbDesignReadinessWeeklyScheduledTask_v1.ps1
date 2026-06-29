#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_MagicOrb_DesignReadiness_Weekly scheduled task + SSOT tier4 registration.
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_MagicOrb_DesignReadiness_Weekly",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
if (-not $OutJson) {
    $OutJson = Join-Path $root "reports\mkm_magic_orb_design_readiness_weekly_scheduled_ops_readiness_v1_latest.json"
}

$runnerExpected = Join-Path $root "scripts\Invoke-MkmMagicOrbDesignReadinessWeeklyRoutine_v1.ps1"
$stackPath = Join-Path $root "docs\final\artifacts\mkm_scheduler_solo_core_stack_v1.json"
$tier4Expected = "\\MKM_MagicOrb_DesignReadiness_Weekly"

$tier4Registered = $false
if (Test-Path -LiteralPath $stackPath) {
    $stackRaw = Get-Content -LiteralPath $stackPath -Raw -Encoding UTF8
    $tier4Registered = $stackRaw -match [Regex]::Escape($tier4Expected)
}

$payload = [ordered]@{
    schema                             = "mkm_magic_orb_design_readiness_weekly_scheduled_ops_readiness_v1"
    generated_at_utc                   = (Get-Date).ToUniversalTime().ToString("o")
    task_name                          = $TaskName
    task_exists                        = $false
    state                              = $null
    runner_exists                      = (Test-Path -LiteralPath $runnerExpected)
    arguments_contain_weekly_routine   = $false
    ssot_tier4_registered              = $tier4Registered
    research_only                      = $true
    ready                              = $false
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
    $payload.task_exists = $true
    $payload.state = [string]$task.State
    $argStr = [string]$task.Actions[0].Arguments
    if ($argStr -match 'Invoke-MkmMagicOrbDesignReadinessWeeklyRoutine_v1\.ps1') {
        $payload.arguments_contain_weekly_routine = $true
    }
}

$payload.ready = $payload.runner_exists -and $payload.ssot_tier4_registered -and (
    (-not $payload.task_exists) -or $payload.arguments_contain_weekly_routine
)

$payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $OutJson -Encoding utf8
Write-Output ("ready={0} task_exists={1} runner_exists={2} ssot_tier4={3}" -f `
    $payload.ready, $payload.task_exists, $payload.runner_exists, $payload.ssot_tier4_registered)
if (-not $payload.runner_exists) { exit 1 }
if (-not $payload.ssot_tier4_registered) { exit 2 }
exit 0
