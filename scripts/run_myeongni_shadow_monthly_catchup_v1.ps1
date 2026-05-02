param(
  [switch]$BackfillPreviousMonth
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot/..")

py "scripts/run_lens_sasang.py"
$root = (Resolve-Path "$PSScriptRoot/..").Path
$logosBatch = Join-Path $root "data\logos\4lens_batch_sample.json"
$logosFixture = Join-Path $root "tests\fixtures\logos_4lens_batch_minimal_v1.json"
if (Test-Path -LiteralPath $logosBatch) {
  py "scripts/run_lens_logos.py" --batch-json $logosBatch
} elseif (Test-Path -LiteralPath $logosFixture) {
  Write-Host "Logos: using tracked fixture (no data/logos/4lens_batch_sample.json)" -ForegroundColor DarkYellow
  py "scripts/run_lens_logos.py" --batch-json $logosFixture
} else {
  py "scripts/run_lens_logos.py" --allow-fallback
}
if ($LASTEXITCODE -ne 0) { throw "run_lens_logos exit $LASTEXITCODE" }
py "scripts/run_lens_myeongni.py"
py "scripts/report_independent_lens_fusion_stub_v0.py"

if ($BackfillPreviousMonth) {
  py "scripts/report_independent_lens_shadow_gate.py" --allow-ts-override --ts-override-utc "2026-03-31T23:59:59Z" --override-label "monthly_backfill_seed_v1"
}

py "scripts/report_independent_lens_shadow_gate.py"
py "scripts/report_independent_lens_shadow_minority_monthly_v1.py"
py "scripts/build_myeongni_commercialization_readiness_packet.py"

Write-Host "DONE: run_myeongni_shadow_monthly_catchup_v1"
