<#
.SYNOPSIS
  Spot-check MKM_ScienceCore_WeeklyGovernance scheduled task (Fact-Lock).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_ScienceCore_WeeklyGovernance",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedRunner = Join-Path $WorkspaceRoot "scripts\Run-ScienceCoreGovernanceBundle_v1.ps1"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments

$okRunner = ($args -match "Run-ScienceCoreGovernanceBundle_v1\.ps1")
$okExtend = ($args -match "-ExtendCalendarStubs")
$okRebuild = ($args -match "-RebuildScience")
$okFullHumanist = ($args -match "-UseFullHumanistPerDate")
$okLongWf = ($args -match "-RunLongWalkforward")
$okHumanistAb = ($args -match "-RunHumanistAb")
$okLogosAb = ($args -match "-RunLogosAb")
$okNewsAblation = ($args -match "-RunNewsWeightAblation")
$okLongLaneCompare = ($args -match "-RunLongWindowLaneCompare")
$okTripleSweep = ($args -match "-RunTripleBlendWeightSweep")
$okPnlBootstrap = ($args -match "-RunPnlBootstrap")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("next_run_time={0}" -f $info.NextRunTime)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $args)
Write-Output ("runner_action_ok={0}" -f $okRunner)
Write-Output ("extend_calendar_stubs_ok={0}" -f $okExtend)
Write-Output ("rebuild_science_ok={0}" -f $okRebuild)
Write-Output ("use_full_humanist_per_date_ok={0}" -f $okFullHumanist)
Write-Output ("run_long_walkforward_ok={0}" -f $okLongWf)
Write-Output ("run_humanist_ab_ok={0}" -f $okHumanistAb)
Write-Output ("run_logos_ab_ok={0}" -f $okLogosAb)
Write-Output ("run_news_weight_ablation_ok={0}" -f $okNewsAblation)
Write-Output ("run_long_window_lane_compare_ok={0}" -f $okLongLaneCompare)
Write-Output ("run_triple_blend_weight_sweep_ok={0}" -f $okTripleSweep)
Write-Output ("run_pnl_bootstrap_ok={0}" -f $okPnlBootstrap)
Write-Output ("runner_script_exists={0}" -f (Test-Path -LiteralPath $expectedRunner))

if (-not ($okRunner -and $okExtend -and $okRebuild -and $okFullHumanist -and $okLongWf -and $okHumanistAb -and $okLogosAb -and $okNewsAblation -and $okLongLaneCompare -and $okTripleSweep -and $okPnlBootstrap)) {
    exit 1
}
exit 0
