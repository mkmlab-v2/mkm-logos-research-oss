# Compression B2B pilot metering smoke: demo seed -> appendix -> summary -> pytest.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "pilot-demo",
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$logRel = "reports/constitution/btrack_pilot/track_a_metering_log_pilot_smoke_v1.jsonl"
$logPath = Join-Path $WorkspaceRoot $logRel
$env:TRACK_A_METERING_LOG_PATH = $logPath

Write-Host "=== build_compression_b2b_pilot_metering_appendix_v1.py --seed-demo ===" -ForegroundColor Cyan
& py scripts/build_compression_b2b_pilot_metering_appendix_v1.py `
    --tenant-id $TenantId `
    --metering-log $logPath `
    --seed-demo
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== run_track_a_metering_summary.py ===" -ForegroundColor Cyan
& py scripts/run_track_a_metering_summary.py --metering-log $logPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipPytest) {
    Write-Host "=== pytest metering appendix ===" -ForegroundColor Cyan
    & py -m pytest tests/test_build_compression_b2b_pilot_metering_appendix_v1.py -q --tb=short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK: Compression pilot metering smoke complete." -ForegroundColor Green
