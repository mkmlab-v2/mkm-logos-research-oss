# Open-bench Moat: auto-build contributor seed (30 masked rows) -> manifest check -> bench chain.
# No real customer data; contributor_provided=true; SEND_GATE HOLD; no auto Track A.

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "contributor-community-v1",
    [int]$Sessions = 30,
    [string]$SeedJsonl = "data/compression/contributions/premium_cs_masked_open_bench_seed_v1.jsonl",
    [string]$WttScratchJsonl = "data/wtt/intake/wtt-premium-cs-auto-local-v1.local.jsonl",
    [switch]$SkipSeedBuild,
    [switch]$SkipManifestCheck,
    [switch]$SkipBenchChain,
    [switch]$DryRun,
    [switch]$RelaxPassGate = $true,
    [switch]$StrictPassGate,
    [switch]$BtrackCsShortContext = $true,
    [switch]$NoBtrackCsShortContext
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

if ($Sessions -lt 10 -or $Sessions -gt 30) {
    Write-Error "Sessions must be 10–30 for open-bench seed (got $Sessions)."
}

$useRelax = $RelaxPassGate -and -not $StrictPassGate
$useBtrack = $BtrackCsShortContext -and -not $NoBtrackCsShortContext

Write-Host "=== Open-bench contributor AUTO (GitHub Moat lane) ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | contributor_provided | SEND_GATE HOLD | no auto Track A" -ForegroundColor Yellow
Write-Host "kit: docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json" -ForegroundColor DarkGray

if ($DryRun) {
    Write-Host "[DryRun] materialize WTT -> export contributor -> manifest -> bench chain" -ForegroundColor DarkGray
    exit 0
}

if (-not $SkipSeedBuild) {
    Write-Host "=== Step 1/4: materialize WTT masked scratch ($Sessions rows) ===" -ForegroundColor Cyan
    & py scripts/materialize_wtt_premium_cs_auto_local_v1.py --sessions $Sessions --out-jsonl $WttScratchJsonl
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "=== Step 2/4: export open-bench contributor seed ===" -ForegroundColor Cyan
    & py scripts/export_open_bench_contributor_corpus_v1.py `
        --jsonl $WttScratchJsonl `
        --out $SeedJsonl `
        --id-prefix contrib-premium-cs-seed `
        --domain-tag customer-support-chat `
        --extra-label premium_cs_icp `
        --extra-label open_bench_community_seed_v1 `
        --provenance-note open_bench_mkm_maintainer_seed_v1 `
        --max-rows $Sessions
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Step 1–2/4: skip seed build (-SkipSeedBuild) ===" -ForegroundColor DarkGray
    if (-not (Test-Path -LiteralPath (Join-Path $WorkspaceRoot ($SeedJsonl -replace '/', '\')))) {
        Write-Error "Missing seed JSONL: $SeedJsonl"
    }
}

if (-not $SkipManifestCheck) {
    Write-Host "=== Step 3/4: manifest + validate entries ===" -ForegroundColor Cyan
    & py scripts/check_compression_contributions_manifest_v1.py --validate-reference
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Step 3/4: skip manifest check ===" -ForegroundColor DarkGray
}

if ($SkipBenchChain) {
    Write-Host "=== Step 4/4: skip bench chain (-SkipBenchChain) ===" -ForegroundColor DarkGray
    Write-Host "Done. Seed: $SeedJsonl" -ForegroundColor Green
    exit 0
}

Write-Host "=== Step 4/4: contributor bench chain ===" -ForegroundColor Cyan
$benchArgs = @(
    "-ContributorJsonl", $SeedJsonl,
    "-TenantId", $TenantId,
    "-MaxCases", "$Sessions",
    "-MinRows", "10"
)
if ($useRelax) { $benchArgs += "-RelaxPassGate" }

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CompressionContributorBenchChain_v1.ps1 @benchArgs
exit $LASTEXITCODE
