# Parity with CI: news_observation_v1 schema + validator tests (no GitHub required).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-NewsObservationContractSmoke.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $root 'tests'))) {
    $root = 'C:\workspace'
}
Set-Location $root

Write-Host "[1/4] pytest news_observation contract..." -ForegroundColor Cyan
& py -m pytest `
    tests/test_news_observation_v1_schema.py `
    tests/test_validate_news_observation_jsonl_v1.py `
    tests/test_check_news_label_join_temporal_v1.py `
    tests/test_build_news_observation_jsonl_from_csv_v1.py `
    tests/test_build_direction_label_bar_jsonl_from_ohlcv_v1.py `
    tests/test_join_news_observation_direction_labels_walkforward_v1.py `
    tests/test_build_direction_label_bar_kospi_csv_smoke_v1.py `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] validate_news_observation_jsonl_v1.py (fixtures)..." -ForegroundColor Cyan
& py scripts/validate_news_observation_jsonl_v1.py `
    --news-jsonl tests/fixtures/news_observation_v1.sample.jsonl `
    --labels-jsonl tests/fixtures/direction_label_bar_v1.sample.jsonl `
    --verify-label-hashes
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/4] temporal join guard (paired fixtures)..." -ForegroundColor Cyan
& py scripts/check_news_label_join_temporal_v1.py `
    --news-jsonl tests/fixtures/news_observation_v1.paired_join_smoke.jsonl `
    --labels-jsonl tests/fixtures/direction_label_bar_v1.paired_join_smoke.jsonl `
    --strict-as-of-date-before-label-date
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$joinOut = Join-Path $env:TEMP ("news_direction_join_smoke_{0}.jsonl" -f $PID)
Write-Host "[4/4] walkforward join (fixtures)..." -ForegroundColor Cyan
& py scripts/join_news_observation_direction_labels_walkforward_v1.py `
    --news-jsonl tests/fixtures/join_walkforward_smoke_v1.news.jsonl `
    --labels-jsonl tests/fixtures/join_walkforward_smoke_v1.labels.jsonl `
    --instrument-id KOSPI `
    --horizon 1d `
    --output $joinOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Run-NewsObservationContractSmoke: OK" -ForegroundColor Green
exit 0
