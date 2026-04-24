param(
  [Parameter(Mandatory = $false)]
  [string]$BaselineMetricsPath = "docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json",

  [Parameter(Mandatory = $false)]
  [string]$LockFilePath = "docs/final/artifacts/orchestration_gate_baseline_lock_v1.json"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $BaselineMetricsPath)) {
  throw "Baseline metrics file not found: $BaselineMetricsPath"
}
if (-not (Test-Path -LiteralPath $LockFilePath)) {
  throw "Baseline lock file not found: $LockFilePath"
}

$lock = Get-Content -LiteralPath $LockFilePath -Raw | ConvertFrom-Json
$actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $BaselineMetricsPath).Hash.ToLower()
$expectedHash = [string]$lock.baseline_sha256
$expectedPath = [string]$lock.baseline_metrics_path

$baselineAbsPath = (Resolve-Path -LiteralPath $BaselineMetricsPath).Path
$expectedPathMatches = $true
if (-not [string]::IsNullOrWhiteSpace($expectedPath)) {
  $expectedCandidate = $expectedPath
  if (-not [System.IO.Path]::IsPathRooted($expectedCandidate)) {
    $expectedCandidate = Join-Path -Path (Get-Location).Path -ChildPath $expectedCandidate
  }
  $expectedAbsPath = (Resolve-Path -LiteralPath $expectedCandidate).Path
  $expectedPathMatches = ($expectedAbsPath -eq $baselineAbsPath)
}

$issues = @()

if ([string]::IsNullOrWhiteSpace($expectedHash)) {
  $issues += [pscustomobject]@{
    issue_code = "BASELINE_LOCK_MISSING_HASH"
    message = "baseline_sha256 is empty in lock file."
  }
}

if (-not $expectedPathMatches) {
  $issues += [pscustomobject]@{
    issue_code = "BASELINE_LOCK_PATH_MISMATCH"
    message = "Lock baseline_metrics_path=$expectedPath does not resolve to BaselineMetricsPath=$BaselineMetricsPath."
  }
}

if ($actualHash -ne $expectedHash) {
  $issues += [pscustomobject]@{
    issue_code = "BASELINE_LOCK_HASH_MISMATCH"
    message = "Baseline hash mismatch. expected=$expectedHash actual=$actualHash"
  }
}

$result = [ordered]@{
  schema = "orchestration_gate_baseline_lock_verify_v1"
  timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
  baseline_metrics_path = $BaselineMetricsPath
  lock_file_path = $LockFilePath
  expected_sha256 = $expectedHash
  actual_sha256 = $actualHash
  passed = ($issues.Count -eq 0)
  issues = @($issues)
}

$result | ConvertTo-Json -Depth 5

if ($issues.Count -gt 0) {
  exit 1
}

exit 0
