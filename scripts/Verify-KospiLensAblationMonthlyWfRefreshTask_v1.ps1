<#
.SYNOPSIS
  Spot-check MKM_KospiLensAblation_MonthlyWfRefresh scheduled task (Fact-Lock).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_KospiLensAblation_MonthlyWfRefresh",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedRunner = Join-Path $WorkspaceRoot "scripts\Run-KospiLensAblationMonthlyWfRefresh_v1.ps1"
$expectedPy = Join-Path $WorkspaceRoot "scripts\run_kospi_lens_ablation_monthly_wf_refresh_v1.py"

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $t) {
    Write-Output "task_name=$TaskName"
    Write-Output "state=missing"
    exit 1
}

$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments

$okRunner = ($args -match "Run-KospiLensAblationMonthlyWfRefresh_v1\.ps1")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("next_run_time={0}" -f $info.NextRunTime)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $args)
Write-Output ("runner_action_ok={0}" -f $okRunner)
Write-Output ("runner_script_exists={0}" -f (Test-Path -LiteralPath $expectedRunner))
Write-Output ("python_runner_exists={0}" -f (Test-Path -LiteralPath $expectedPy))

if (-not ($okRunner -and (Test-Path -LiteralPath $expectedRunner) -and (Test-Path -LiteralPath $expectedPy))) {
    exit 1
}
exit 0
