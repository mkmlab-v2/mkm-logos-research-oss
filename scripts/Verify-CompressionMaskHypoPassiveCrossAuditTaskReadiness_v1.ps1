#Requires -Version 5.1
<#
.SYNOPSIS
  Readiness spot-check for MKM_Compression_MaskHypoPassiveCrossAudit_Daily.

.NOTES
  Register with scripts/Register-CompressionMaskHypoPassiveCrossAuditDailyTask.ps1
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM_Compression_MaskHypoPassiveCrossAudit_Daily",
    [switch]$RequireTask
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\Run-CompressionMaskHypoPassiveCrossAudit_v1.ps1"
$pyRunner = Join-Path $WorkspaceRoot "scripts\run_compression_mask_hypo_passive_cross_audit_v1.py"
$staging = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_mask_shadow_registry_staging_v1.json"

$missing = @()
foreach ($p in @($runner, $pyRunner, $staging)) {
    if (-not (Test-Path -LiteralPath $p)) { $missing += $p }
}
if ($missing.Count -gt 0) {
    Write-Error ("missing_paths: {0}" -f ($missing -join "; "))
    exit 1
}

$taskExists = $false
$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($t) {
    $taskExists = $true
    $info = Get-ScheduledTaskInfo -InputObject $t
    $a = $t.Actions[0]
    Write-Output "task_name=$TaskName"
    Write-Output ("state={0}" -f $t.State)
    Write-Output ("last_run_time={0}" -f $info.LastRunTime)
    Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
    Write-Output ("execute={0}" -f $a.Execute)
    Write-Output ("arguments={0}" -f $a.Arguments)
    Write-Output ("working_directory={0}" -f $a.WorkingDirectory)
} else {
    Write-Output "task_name=$TaskName"
    Write-Output "state=missing"
}

Write-Output ("task_exists={0}" -f $taskExists)
Write-Output "runner=$runner"
Write-Output "py_runner=$pyRunner"
Write-Output "staging_pointer=$staging"
Write-Output "lane=compression_mask_hypo_passive"
Write-Output "forbidden_lane=kospi_evening_prophecy"

if ($RequireTask -and -not $taskExists) {
    Write-Error "scheduled task not registered: $TaskName"
    exit 1
}

exit 0
