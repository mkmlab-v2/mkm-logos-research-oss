# Saving the News — showroom topology slice + local gateway ingest smoke (research_only).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-SavingTheNewsShowroomLocalSmoke_v1.ps1

param(
    [int]$Port = 8788,
    [switch]$SkipDeployStaging,
    [switch]$SkipIngest
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/5] Phase3 stub refresh (active_character_id)..." -ForegroundColor Cyan
& py scripts/eval_saving_the_news_phase3_truth_gating_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/6] Topology + matrix panel slices (public facade)..." -ForegroundColor Cyan
& py scripts/build_saving_the_news_showroom_topology_slice_v1.py --fail-if-missing --display-mode public_showroom
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2b/6] Public copy gate..." -ForegroundColor Cyan
& py scripts/check_saving_the_news_public_copy_gate_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/6] Ensure public event gateway on port $Port..." -ForegroundColor Cyan
$ensure = Join-Path $root 'projects\bitcoin-trading\ops\windows-rehearsal\ensure_public_event_gateway.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $ensure -Port $Port
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipIngest) {
    Write-Host "[4/6] Ingest stub -> http://127.0.0.1:$Port ..." -ForegroundColor Cyan
    & py scripts/ingest_saving_the_news_public_event_local_v1.py --api-base "http://127.0.0.1:$Port"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[4/6] Ingest skipped (-SkipIngest)" -ForegroundColor Yellow
}

if (-not $SkipDeployStaging) {
    Write-Host "[5/6] Deploy static to .showroom_staging..." -ForegroundColor Cyan
    $mvp = Join-Path $root 'projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp'
    $staging = Join-Path $root 'projects\bitcoin-trading\ops\windows-rehearsal\.showroom_staging'
    New-Item -ItemType Directory -Path $staging -Force | Out-Null
    $copies = @(
        @{ Src = Join-Path $mvp 'public_showroom_saving_the_news_matrix_v1.html'; Name = 'public_showroom_saving_the_news_matrix_v1.html' },
        @{ Src = (Join-Path $root 'docs\final\artifacts\saving_the_news_matrix_panel_slice_v1_latest.json'); Name = 'saving_the_news_matrix_panel_slice_v1_latest.json' },
        @{ Src = (Join-Path $root 'docs\final\artifacts\saving_the_news_showroom_topology_slice_v1_latest.json'); Name = 'saving_the_news_showroom_topology_slice_v1_latest.json' }
    )
    foreach ($c in $copies) {
        if (-not (Test-Path -LiteralPath $c.Src)) {
            Write-Host "  skip missing: $($c.Src)" -ForegroundColor Yellow
            continue
        }
        Copy-Item -LiteralPath $c.Src -Destination (Join-Path $staging $c.Name) -Force
        Write-Host "  copied $($c.Name)" -ForegroundColor DarkGray
    }
} else {
    Write-Host "[5/6] Staging deploy skipped (-SkipDeployStaging)" -ForegroundColor Yellow
}

Write-Host "Run-SavingTheNewsShowroomLocalSmoke_v1: OK" -ForegroundColor Green
Write-Host "  Panel: file://.../.showroom_staging/public_showroom_saving_the_news_matrix_v1.html?api=http://127.0.0.1:$Port" -ForegroundColor DarkGray
exit 0
