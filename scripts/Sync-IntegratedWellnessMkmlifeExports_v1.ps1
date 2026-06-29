# Copy IWS v2 mkmlife render JSON to mkm-life public/data (ask-one ingest).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RunChain
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
$chainDir = Join-Path $root "reports\integrated_wellness_solution_v2_chain"
$srcJson = Join-Path $chainDir "render_mkmlife_latest.json"
$srcMd = Join-Path $chainDir "mkmlife_report_latest.md"
$destDir = Join-Path $root "projects\mkm\mkm-life\public\data"
$destJson = Join-Path $destDir "integrated_wellness_mkmlife_report_v1.json"
$destMd = Join-Path $destDir "integrated_wellness_mkmlife_report_v1.md"

if ($RunChain) {
    & py (Join-Path $root "scripts\run_integrated_wellness_solution_v2_chain_v1.py") --validate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py (Join-Path $root "scripts\adapt_integrated_wellness_personadiary_export_v1.py") 2>$null
}

if (-not (Test-Path $srcJson)) {
    Write-Host "[iws-mkmlife] chain missing — running publish with default seed" -ForegroundColor Yellow
    & py (Join-Path $root "scripts\publish_integrated_wellness_solution_v2_exports_v1.py") `
        --seed-json (Join-Path $root "docs\final\artifacts\fixtures\integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json") `
        --out-dir $chainDir
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Test-Path $srcJson)) { throw "missing $srcJson" }

New-Item -ItemType Directory -Force -Path $destDir | Out-Null
Copy-Item -Force $srcJson $destJson
if (Test-Path $srcMd) { Copy-Item -Force $srcMd $destMd }
Write-Host "[iws-mkmlife] OK: $destJson"
