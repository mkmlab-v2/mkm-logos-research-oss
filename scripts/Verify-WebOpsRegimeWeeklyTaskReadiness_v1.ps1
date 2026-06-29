#Requires -Version 5.1
<#
.SYNOPSIS
  Spot-check MKM_WebOps_Regime_Weekly scheduled task action.
#>
param(
    [string]$TaskName = "MKM_WebOps_Regime_Weekly",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments
$okRoutine = ($args -match "Invoke-WebOpsRegimeWeeklyRoutine_v1\.ps1")
$okLegacyBundle = ($args -match "Run-WebOpsRegimeFullBundle_v1\.ps1")
$okNoSeed = ($args -match "-NoSeedBaselines" -or $args -match "--no-seed-baselines")
$okDual = ($args -match "-RequireDualAlignment" -or $args -match "--require-dual-alignment")
$okDrift = ($args -match "-FailOnPointerDrift" -or $args -match "--fail-on-pointer-drift")
$okSkipCdp = ($args -match "-SkipLiveCdp")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $args)
Write-Output ("weekly_routine_ok={0}" -f $okRoutine)
Write-Output ("legacy_bundle_only_ok={0}" -f $okLegacyBundle)
Write-Output ("no_seed_baselines_ok={0}" -f $okNoSeed)
Write-Output ("require_dual_alignment_ok={0}" -f $okDual)
Write-Output ("fail_on_pointer_drift_ok={0}" -f $okDrift)
Write-Output ("skip_live_cdp_ok={0}" -f $okSkipCdp)
Write-Output ("ops_memory_overlay_in_routine={0}" -f $okRoutine)

if (-not ($okRoutine -or $okLegacyBundle)) { exit 1 }
if (-not ($okNoSeed -and $okDual -and $okDrift)) { exit 1 }
if ($okRoutine -and -not $okSkipCdp) { exit 1 }
exit 0
