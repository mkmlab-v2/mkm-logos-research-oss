param(
  [Parameter(Mandatory = $false)]
  [string]$BaselineMetricsPath = "docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json",

  [Parameter(Mandatory = $false)]
  [string]$LockFilePath = "docs/final/artifacts/orchestration_gate_baseline_lock_v1.json",

  [Parameter(Mandatory = $false)]
  [string]$ApprovedBy = "human_review_required",

  [Parameter(Mandatory = $false)]
  [switch]$ConfirmUpdate
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmUpdate) {
  throw "Baseline lock update requires explicit approval. Re-run with -ConfirmUpdate."
}

if (-not (Test-Path -LiteralPath $BaselineMetricsPath)) {
  throw "Baseline metrics file not found: $BaselineMetricsPath"
}
if (-not (Test-Path -LiteralPath $LockFilePath)) {
  throw "Baseline lock file not found: $LockFilePath"
}

$lock = Get-Content -LiteralPath $LockFilePath -Raw | ConvertFrom-Json
$baselineHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $BaselineMetricsPath).Hash.ToLower()

$updated = [ordered]@{
  schema = "orchestration_gate_baseline_lock_v1"
  updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  approved_by = $ApprovedBy
  baseline_metrics_path = $BaselineMetricsPath
  baseline_sha256 = $baselineHash
  notes = "Update this lock file only after human-reviewed baseline refresh. Prevents silent baseline drift from inflating improvement metrics."
}

$json = $updated | ConvertTo-Json -Depth 5
$json | Set-Content -LiteralPath $LockFilePath -Encoding utf8

Write-Output $json
