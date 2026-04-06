<#
.SYNOPSIS
  Check health of war-prolongation benchmark automation.

.DESCRIPTION
  Verifies:
  - Scheduled task existence and last run result
  - Latest resilient run log status
  - Latest benchmark bundle gate decision
  Writes machine-readable health JSON to artifacts.
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "MKM-War-Prolongation-Benchmark-Daily"
)

$ErrorActionPreference = "Stop"

$art = Join-Path $WorkspaceRoot "docs/final/artifacts"
if (-not (Test-Path -LiteralPath $art)) {
  New-Item -ItemType Directory -Path $art -Force | Out-Null
}

$outPath = Join-Path $art "war_prolongation_benchmark_health_latest.json"
$runLogPath = Join-Path $art "war_prolongation_resilient_run_latest.json"
$bundlePath = Join-Path $art "war_prolongation_benchmark_bundle_20260406.json"

function Read-JsonOrNull {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  try {
    return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
  } catch {
    return $null
  }
}

$taskInfo = $null
$taskState = $null
$taskExists = $false
try {
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
  $taskState = $task.State.ToString()
  $taskExists = $true
} catch {
  $taskExists = $false
}

$runLog = Read-JsonOrNull -Path $runLogPath
$bundle = Read-JsonOrNull -Path $bundlePath

$issues = @()
if (-not $taskExists) { $issues += "task_missing" }
if ($taskExists -and $taskInfo.LastTaskResult -ne 0) { $issues += "task_last_result_nonzero" }
if ($null -eq $runLog) { $issues += "run_log_missing_or_invalid" }
elseif ($runLog.status -ne "ok" -and $runLog.status -ne "dry_run") { $issues += "resilient_run_not_ok" }
if ($null -eq $bundle) { $issues += "bundle_missing_or_invalid" }
elseif ($bundle.snapshot.gate_decision -ne "GO") { $issues += "gate_not_go" }

$status = if ($issues.Count -eq 0) { "ok" } else { "attention" }

$payload = [ordered]@{
  schema = "war_prolongation_benchmark_health_v1"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  task = [ordered]@{
    name = $TaskName
    exists = $taskExists
    state = $taskState
    last_task_result = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
    last_run_time = if ($taskInfo) { $taskInfo.LastRunTime } else { $null }
    next_run_time = if ($taskInfo) { $taskInfo.NextRunTime } else { $null }
  }
  latest_run_log = if ($runLog) { $runLog } else { $null }
  latest_bundle_snapshot = if ($bundle) { $bundle.snapshot } else { $null }
  status = $status
  issues = $issues
}

$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8
Write-Host "WROTE: $outPath"
if ($status -eq "ok") {
  Write-Host "Health status: OK" -ForegroundColor Green
} else {
  Write-Warning ("Health status: ATTENTION ({0})" -f ($issues -join ", "))
}

