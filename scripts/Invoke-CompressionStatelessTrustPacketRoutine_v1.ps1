#Requires -Version 5.1
<#
.SYNOPSIS
  Stateless Trust Packet routine: V2 pytest, Golden 40 regression, customer PoC smoke, lossless exact restore.

.DESCRIPTION
  Use after compression automation chain or standalone. Does not edit MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json.

.PARAMETER SkipPytest
  Skip tests/test_compression_token_api_v2_stub.py (e.g. when chain already ran it).

.PARAMETER SkipGoldenBenchRegression
  Skip check_compression_golden_bench_regression_v1.py.

.PARAMETER SkipCustomerPoc
  Skip JSONL PoC on data/compression/stateless_poc_smoke_v1.jsonl.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipPytest,
    [switch]$SkipGoldenBenchRegression,
    [switch]$SkipCustomerPoc
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if (-not $SkipPytest) {
    Write-Host "=== pytest tests/test_compression_token_api_v2_stub.py ===" -ForegroundColor Cyan
    & py -m pytest (Join-Path $WorkspaceRoot "tests\test_compression_token_api_v2_stub.py") -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipGoldenBenchRegression) {
    Write-Host "=== check_compression_golden_bench_regression_v1.py ===" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\check_compression_golden_bench_regression_v1.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipCustomerPoc) {
    $fixture = Join-Path $WorkspaceRoot "data\compression\stateless_poc_smoke_v1.jsonl"
    if (-not (Test-Path -LiteralPath $fixture)) {
        throw "Missing PoC fixture: $fixture"
    }
    Write-Host "=== run_customer_compression_stateless_poc_v1.py (semantic_general) ===" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\run_customer_compression_stateless_poc_v1.py") `
        --workspace-root $WorkspaceRoot `
        --input-jsonl $fixture `
        --max-cases 10 `
        --loss-profile semantic_general
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $losslessFixture = Join-Path $WorkspaceRoot "data\compression\stateless_poc_lossless_v1.jsonl"
    if (-not (Test-Path -LiteralPath $losslessFixture)) {
        throw "Missing lossless PoC fixture: $losslessFixture"
    }
    Write-Host "=== run_customer_compression_stateless_poc_v1.py (lossless_text, exact restore) ===" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\run_customer_compression_stateless_poc_v1.py") `
        --workspace-root $WorkspaceRoot `
        --input-jsonl $losslessFixture `
        --max-cases 10 `
        --loss-profile lossless_text `
        --out-json (Join-Path $WorkspaceRoot "reports\customer_compression_stateless_poc_lossless_v1_latest.json")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[Invoke-CompressionStatelessTrustPacketRoutine_v1] OK" -ForegroundColor Green
exit 0
