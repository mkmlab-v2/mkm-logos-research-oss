<#
.SYNOPSIS
  Apply news third-party reproducibility evidence from a fixed dropzone folder.

.DESCRIPTION
  Looks for required files under reports/news_repro/latest and applies them to
  news_third_party_repro_bundle_latest.json, then rebuilds news readiness.
#>
[CmdletBinding()]
param(
    [string] $Dropzone = "C:\workspace\reports\news_repro\latest",
    [string] $RunnerId = "external-runner-unknown",
    [string] $Signer = "external-signer-unknown"
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"

$manifest = Join-Path $Dropzone "external_runner_manifest.json"
$rawLog = Join-Path $Dropzone "raw_benchmark.log"
$digest = Join-Path $Dropzone "independent_result_digest.json"
$signed = Join-Path $Dropzone "signed_repro_statement.txt"

$missing = @()
foreach ($p in @($manifest, $rawLog, $digest, $signed)) {
    if (-not (Test-Path -LiteralPath $p)) { $missing += $p }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing required third-party files:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Drop files into: $Dropzone" -ForegroundColor Cyan
    Write-Host "Expected names:" -ForegroundColor Cyan
    Write-Host " - external_runner_manifest.json"
    Write-Host " - raw_benchmark.log"
    Write-Host " - independent_result_digest.json"
    Write-Host " - signed_repro_statement.txt"
    exit 2
}

Set-Location $root
py "scripts/apply_news_third_party_repro_evidence_v1.py" `
  --manifest-json $manifest `
  --raw-log $rawLog `
  --result-digest-json $digest `
  --signed-statement $signed `
  --runner-id $RunnerId `
  --signer $Signer
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py "scripts/build_news_benchmark_readiness_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Applied third-party repro evidence and rebuilt readiness." -ForegroundColor Green
exit 0

