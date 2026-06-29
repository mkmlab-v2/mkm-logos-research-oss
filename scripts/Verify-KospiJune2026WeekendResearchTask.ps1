<#
.SYNOPSIS
  Spot-check MKM KOSPI June 2026 weekend research scheduled task [HYPO].

.EXAMPLE
  pwsh -File scripts/Verify-KospiJune2026WeekendResearchTask.ps1
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_Kospi_June2026_Weekend_Research",
    [string]$WorkspaceRoot = "C:\workspace"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$fail = $false

$expectedBundle = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026WeekendResearchBundle_v1.ps1"
if (-not (Test-Path -LiteralPath $expectedBundle)) {
    Write-Error "Missing bundle script: $expectedBundle"
    exit 2
}

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $t) {
    Write-Output "task_present=false"
    exit 1
}

$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]
$args = [string]$a.Arguments

$bundleOk = ($args -match "Invoke-KospiJune2026WeekendResearchBundle_v1\.ps1")
$yearOk = ($args -match "-YearMonth\s+2026-06")

Write-Output "task_name=$TaskName"
Write-Output ("state={0}" -f $t.State)
Write-Output ("next_run_time={0}" -f $info.NextRunTime)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("weekend_bundle_action_ok={0}" -f $bundleOk)
Write-Output ("year_month_2026_06_ok={0}" -f $yearOk)

if (-not ($bundleOk -and $yearOk)) { $fail = $true }

$sched = Join-Path $WorkspaceRoot "reports\kospi_june2026_weekend_research_schedule_latest.json"
Write-Output ("schedule_json_ok={0}" -f (Test-Path -LiteralPath $sched))

if (-not (Test-Path -LiteralPath $sched)) { $fail = $true }

if ($fail) { exit 1 }
exit 0
