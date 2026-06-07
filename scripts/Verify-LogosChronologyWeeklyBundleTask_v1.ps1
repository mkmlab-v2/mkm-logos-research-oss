<#
.SYNOPSIS
  Spot-check MKM_Logos_Chronology_WeeklyBundle scheduled task (Fact-Lock).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_Logos_Chronology_WeeklyBundle",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedBuildV2 = Join-Path $WorkspaceRoot "scripts\build_logos_chronology_v2_ai_synthesis_v1.py"
$expectedBundle = Join-Path $WorkspaceRoot "scripts\Invoke-LogosChronologyParallelBundle_v1.ps1"
$expectedHorizon = Join-Path $WorkspaceRoot "scripts\build_logos_macro_horizon_2030_scenario_v1.py"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments

$okV2 = ($args -match "build_logos_chronology_v2_ai_synthesis_v1\.py")
$okBundle = ($args -match "Invoke-LogosChronologyParallelBundle_v1\.ps1")
$bundleHasHorizonStep = (Test-Path -LiteralPath $expectedHorizon) -and (
    (Get-Content -LiteralPath $expectedBundle -Raw) -match "build_logos_macro_horizon_2030_scenario_v1\.py"
)

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("next_run_time={0}" -f $info.NextRunTime)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $args)
Write-Output ("build_v2_action_ok={0}" -f $okV2)
Write-Output ("parallel_bundle_action_ok={0}" -f $okBundle)
Write-Output ("bundle_includes_horizon_2030_step={0}" -f $bundleHasHorizonStep)
Write-Output ("build_v2_script_exists={0}" -f (Test-Path -LiteralPath $expectedBuildV2))
Write-Output ("parallel_bundle_script_exists={0}" -f (Test-Path -LiteralPath $expectedBundle))

if (-not ($okV2 -and $okBundle -and $bundleHasHorizonStep)) {
    exit 1
}
exit 0
