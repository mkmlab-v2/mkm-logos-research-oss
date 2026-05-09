[CmdletBinding()]
param(
  [string]$WorkspaceRoot = "",
  [int]$MaxGoNoGoAgeHours = 3,
  [switch]$AllowExpectedSecurityDrift
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  } else {
    $WorkspaceRoot = (Get-Location).Path
  }
}

Set-Location -LiteralPath $WorkspaceRoot

function Get-TaskHealth([string]$TaskName) {
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if (-not $task) {
    return [pscustomobject]@{
      task_name = $TaskName
      exists = $false
      state = "MISSING"
      last_task_result = $null
      last_run_time = $null
      ok = $false
      reason = "task_missing"
    }
  }

  $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
  $lastResult = if ($info) { $info.LastTaskResult } else { $null }
  $state = "$($task.State)"
  $ok = ($state -in @("Ready", "Running")) -and ($lastResult -eq 0 -or $null -eq $lastResult)
  $reason = if ($ok) { "ok" } else { "state_or_last_result_not_ok" }

  return [pscustomobject]@{
    task_name = $TaskName
    exists = $true
    state = $state
    last_task_result = $lastResult
    last_run_time = if ($info) { $info.LastRunTime } else { $null }
    next_run_time = if ($info) { $info.NextRunTime } else { $null }
    ok = $ok
    reason = $reason
  }
}

function Read-Json([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  try { return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json }
  catch { return $null }
}

$taskNames = @(
  "MKM-Trading-Observation-Loop-2H",
  "MKM-Trading-Execution-Readiness-Loop-2H",
  "MKM-AmsaengEosa-Monitoring-Bundle-60min",
  "MKM-Security-Integrity-Check-5min"
)

$tasks = @()
foreach ($name in $taskNames) {
  $tasks += Get-TaskHealth -TaskName $name
}

$goNoGoPath = Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json"
$secPath = Join-Path $WorkspaceRoot "reports\security_integrity_status_latest.json"
$goNoGo = Read-Json -Path $goNoGoPath
$sec = Read-Json -Path $secPath

$goNoGoOk = $false
$goNoGoAgeHours = $null
if ($goNoGo -and $goNoGo.generated_at_utc) {
  $generated = [datetimeoffset]::Parse("$($goNoGo.generated_at_utc)")
  $age = [datetimeoffset]::UtcNow - $generated.ToUniversalTime()
  $goNoGoAgeHours = [math]::Round($age.TotalHours, 3)
  $goNoGoOk = ($goNoGo.go_no_go -eq "GO") -and ($age.TotalHours -le $MaxGoNoGoAgeHours)
}

$securityOk = $false
$securityReason = "security_status_not_green"
if ($sec -and $sec.status) {
  $statusText = "$($sec.status)"
  if ($statusText -eq "GREEN") {
    $securityOk = $true
    $securityReason = "ok"
  } elseif ($AllowExpectedSecurityDrift -and $statusText -eq "RED") {
    $expected = @(
      ".env",
      "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
      "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
    )
    $changed = @()
    if ($sec.changed_paths) {
      foreach ($p in $sec.changed_paths) { $changed += "$p" }
    }
    $unexpected = @($changed | Where-Object { $_ -notin $expected })
    if (@($unexpected).Count -eq 0) {
      $securityOk = $true
      $securityReason = "expected_drift_only"
    } else {
      $securityReason = "unexpected_drift_detected"
    }
  }
}

$tasksOk = @($tasks | Where-Object { -not $_.ok }).Count -eq 0
$overallOk = $tasksOk -and $goNoGoOk -and $securityOk

$report = [ordered]@{
  schema = "trading_automation_health_v1"
  generated_at_utc = [datetime]::UtcNow.ToString("o")
  overall_ok = $overallOk
  tasks_ok = $tasksOk
  security_ok = $securityOk
  security_reason = $securityReason
  go_no_go_ok = $goNoGoOk
  go_no_go_age_hours = $goNoGoAgeHours
  max_go_no_go_age_hours = $MaxGoNoGoAgeHours
  go_no_go = if ($goNoGo) { $goNoGo.go_no_go } else { $null }
  task_health = $tasks
}

$outPath = Join-Path $WorkspaceRoot "reports\trading_automation_health_latest.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outPath -Encoding UTF8

Write-Output "trading_automation_health_written=$outPath"
Write-Output "overall_ok=$overallOk tasks_ok=$tasksOk security_ok=$securityOk go_no_go_ok=$goNoGoOk"
if (-not $overallOk) {
  exit 1
}
exit 0
