param(
  [Parameter(Mandatory = $false)]
  [string]$CurrentMetricsPath = "docs/final/artifacts/bench_l1_api_load_latest.json",

  [Parameter(Mandatory = $false)]
  [string]$BaselineMetricsPath = "docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json"
)

$ErrorActionPreference = "Stop"

function Get-JsonValueOrNull {
  param(
    [Parameter(Mandatory = $true)] $Obj,
    [Parameter(Mandatory = $true)] [string]$Path
  )

  $segments = $Path.Split(".")
  $cursor = $Obj
  foreach ($segment in $segments) {
    if ($null -eq $cursor) { return $null }
    $prop = $cursor.PSObject.Properties[$segment]
    if ($null -eq $prop) { return $null }
    $cursor = $prop.Value
  }
  return $cursor
}

function To-Double {
  param([Parameter(Mandatory = $false)] $Value)
  if ($null -eq $Value) { return $null }
  try {
    return [double]$Value
  } catch {
    return $null
  }
}

if (-not (Test-Path -LiteralPath $CurrentMetricsPath)) {
  throw "Current metrics file not found: $CurrentMetricsPath"
}
if (-not (Test-Path -LiteralPath $BaselineMetricsPath)) {
  throw "Baseline metrics file not found: $BaselineMetricsPath"
}

$current = Get-Content -LiteralPath $CurrentMetricsPath -Raw | ConvertFrom-Json
$baseline = Get-Content -LiteralPath $BaselineMetricsPath -Raw | ConvertFrom-Json

$currentLatency = To-Double (Get-JsonValueOrNull -Obj $current -Path "latency_ms.p95")
$baselineLatency = To-Double (Get-JsonValueOrNull -Obj $baseline -Path "latency_ms.p95")

if ($null -eq $currentLatency) {
  $currentLatency = To-Double (Get-JsonValueOrNull -Obj $current -Path "bench_latency_p95_ms")
}
if ($null -eq $baselineLatency) {
  $baselineLatency = To-Double (Get-JsonValueOrNull -Obj $baseline -Path "bench_latency_p95_ms")
}

$currentError = To-Double (Get-JsonValueOrNull -Obj $current -Path "error_rate")
$baselineError = To-Double (Get-JsonValueOrNull -Obj $baseline -Path "error_rate")

if ($null -eq $currentError) {
  $currentError = To-Double (Get-JsonValueOrNull -Obj $current -Path "bench_error_rate")
}
if ($null -eq $baselineError) {
  $baselineError = To-Double (Get-JsonValueOrNull -Obj $baseline -Path "bench_error_rate")
}

if ($null -eq $currentLatency -or $null -eq $baselineLatency) {
  throw "Cannot compute latency improvement: missing p95 latency in current/baseline."
}
if ($null -eq $currentError -or $null -eq $baselineError) {
  throw "Cannot compute error-rate reduction: missing error_rate in current/baseline."
}

if ($baselineLatency -le 0) {
  throw "Invalid baseline latency: $baselineLatency"
}

$latencyImprovement = (($baselineLatency - $currentLatency) / $baselineLatency) * 100.0

if ($baselineError -eq 0) {
  if ($currentError -eq 0) {
    $errorRateReduction = 100.0
  } else {
    $errorRateReduction = -100.0
  }
} else {
  $errorRateReduction = (($baselineError - $currentError) / $baselineError) * 100.0
}

$result = [ordered]@{
  schema = "orchestration_gate_metrics_v1"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  current_metrics_path = $CurrentMetricsPath
  baseline_metrics_path = $BaselineMetricsPath
  current = [ordered]@{
    latency_p95_ms = $currentLatency
    error_rate = $currentError
  }
  baseline = [ordered]@{
    latency_p95_ms = $baselineLatency
    error_rate = $baselineError
  }
  derived = [ordered]@{
    latency_improvement = [Math]::Round($latencyImprovement, 3)
    error_rate_reduction = [Math]::Round($errorRateReduction, 3)
  }
}

$result | ConvertTo-Json -Depth 6
