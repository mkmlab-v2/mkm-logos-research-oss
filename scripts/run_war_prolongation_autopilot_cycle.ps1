<#
.SYNOPSIS
  Run one full autopilot cycle for war-prolongation benchmark.

.DESCRIPTION
  1) Execute resilient benchmark chain
  2) Refresh health report
  3) Emit promotion readiness flag JSON (GO => true, else false)
#>
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [int]$MaxAttempts = 2,
  [int]$BackoffSeconds = 5
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$art = Join-Path $WorkspaceRoot "docs/final/artifacts"
if (-not (Test-Path -LiteralPath $art)) {
  New-Item -ItemType Directory -Path $art -Force | Out-Null
}

Write-Host "==> resilient benchmark run"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/run_war_prolongation_benchmark_resilient.ps1") `
  -WorkspaceRoot $WorkspaceRoot `
  -MaxAttempts $MaxAttempts `
  -BackoffSeconds $BackoffSeconds
if ($LASTEXITCODE -ne 0) { throw "resilient benchmark failed: $LASTEXITCODE" }

Write-Host "==> health check"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts/check_war_prolongation_benchmark_health.ps1") `
  -WorkspaceRoot $WorkspaceRoot `
  -TaskName "MKM-War-Prolongation-Autopilot-Daily"
if ($LASTEXITCODE -ne 0) { throw "health check failed: $LASTEXITCODE" }

$bundlePath = Join-Path $art "war_prolongation_benchmark_bundle_20260406.json"
$flagPath = Join-Path $art "war_prolongation_promotion_ready_latest.json"

if (-not (Test-Path -LiteralPath $bundlePath)) {
  throw "bundle missing: $bundlePath"
}

$bundle = Get-Content -LiteralPath $bundlePath -Raw | ConvertFrom-Json
$decision = [string]($bundle.snapshot.gate_decision)
$isReady = $decision -eq "GO"

$flag = [ordered]@{
  schema = "war_prolongation_promotion_ready_v1"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  gate_decision = $decision
  promotion_ready = $isReady
  source_bundle = "docs/final/artifacts/war_prolongation_benchmark_bundle_20260406.json"
  note = if ($isReady) { "Promotion-ready by gate decision." } else { "Hold: gate decision is not GO." }
}
$flag | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $flagPath -Encoding UTF8

Write-Host "WROTE: $flagPath"

$statusPath = Join-Path $art "war_prolongation_autopilot_status_latest.json"
$status = [ordered]@{
  schema = "war_prolongation_autopilot_status_v1"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  cycle_ok = $true
  monitored_task = "MKM-War-Prolongation-Autopilot-Daily"
  promotion_ready = $isReady
  gate_decision = $decision
  references = @{
    bundle = "docs/final/artifacts/war_prolongation_benchmark_bundle_20260406.json"
    health = "docs/final/artifacts/war_prolongation_benchmark_health_latest.json"
    promotion_flag = "docs/final/artifacts/war_prolongation_promotion_ready_latest.json"
  }
}
$status | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Host "WROTE: $statusPath"
Write-Host "OK: autopilot cycle completed." -ForegroundColor Green

