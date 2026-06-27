# Contributor masked JSONL -> validate -> bootstrap -> stateless PoC -> promotion candidate (B-track).
param(
    [Parameter(Mandatory = $true)]
    [string]$ContributorJsonl,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "contributor-community-v1",
    [int]$MaxCases = 30,
    [int]$MinRows = 10,
    [string]$Sku = "MKM-CHAT-D1",
    [ValidateSet("economy", "fidelity", "literal")]
    [string]$CompressionProfile = "economy",
    [switch]$RelaxPassGate,
    [switch]$SkipIntake,
    [switch]$DryRun,
    [string]$MustKeepOverlayJson = "",
    [int]$ShortContextTokenThreshold = 30,
    [double]$ShortContextMaxSavingRate = 0.30,
    [switch]$NoOverlay,
    [switch]$NoShortContextCap
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$JsonlPath = if ([System.IO.Path]::IsPathRooted($ContributorJsonl)) {
    (Resolve-Path -LiteralPath $ContributorJsonl).Path
} else {
    (Resolve-Path -LiteralPath (Join-Path $WorkspaceRoot $ContributorJsonl)).Path
}

if (-not (Test-Path -LiteralPath $JsonlPath)) {
    Write-Error "Contributor JSONL not found: $JsonlPath"
}

Write-Host "=== Compression contributor bench chain (B-track) ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | SEND_GATE HOLD | no auto Track A" -ForegroundColor Yellow
Write-Host "kit: docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json" -ForegroundColor DarkGray

if ($DryRun) {
    Write-Host "[DryRun] validate -> bootstrap -> poc -> candidate" -ForegroundColor DarkGray
    exit 0
}

$ValidateJson = "reports/compression_contributor_jsonl_validate_${TenantId}_latest.json"

Write-Host "=== Step 1/4: validate contributor JSONL ===" -ForegroundColor Cyan
& py scripts/validate_compression_contributor_jsonl_v1.py --jsonl $JsonlPath --min-rows $MinRows --out-json $ValidateJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$PocJson = "reports/customer_compression_stateless_poc_$TenantId`_v1_latest.json"
$CorpusJsonl = "data/compression/stateless_poc_prospect_$TenantId`_v1.jsonl"

if (-not $SkipIntake) {
    Write-Host "=== Step 2/4: bootstrap contributor tenant ===" -ForegroundColor Cyan
    & py scripts/bootstrap_compression_pilot_tenant_v1.py `
        --tenant-id $TenantId `
        --source-jsonl $JsonlPath `
        --max-cases $MaxCases `
        --contributor-provided
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Step 2/4: skipped bootstrap (-SkipIntake) ===" -ForegroundColor DarkGray
}

Write-Host "=== Step 3/4: stateless PoC on tenant corpus ===" -ForegroundColor Cyan
$overlayPath = $MustKeepOverlayJson
if (-not $NoOverlay) {
    if (-not $overlayPath) {
        $overlayPath = Join-Path $WorkspaceRoot "docs/final/artifacts/tenant_${TenantId}_must_keep_overlay_v1.json"
    } elseif (-not [System.IO.Path]::IsPathRooted($overlayPath)) {
        $overlayPath = Join-Path $WorkspaceRoot ($overlayPath -replace '/', '\')
    }
    if (-not (Test-Path -LiteralPath $overlayPath)) {
        Write-Host "=== Step 3a/4: extract must_keep overlay (missing) ===" -ForegroundColor Cyan
        & py scripts/extract_tenant_must_keep_from_corpus_v1.py `
            --tenant-id $TenantId `
            --input-jsonl $CorpusJsonl
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
$pocArgs = @(
    "scripts/run_customer_compression_stateless_poc_v1.py",
    "--input-jsonl", $CorpusJsonl,
    "--out-json", $PocJson,
    "--max-cases", $MaxCases,
    "--compression-profile", $CompressionProfile,
    "--sku", $Sku
)
if (-not $NoOverlay -and (Test-Path -LiteralPath $overlayPath)) {
    $pocArgs += @("--must-keep-overlay-json", ($overlayPath -replace '\\', '/'))
}
if (-not $NoShortContextCap) {
    $pocArgs += @(
        "--short-context-token-threshold", "$ShortContextTokenThreshold",
        "--short-context-max-saving-rate", "$ShortContextMaxSavingRate"
    )
}
if ($RelaxPassGate) { $pocArgs += "--relax-pass-gate" }
& py @pocArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "PoC exit $LASTEXITCODE (candidate may still be built for review)" -ForegroundColor Yellow
}

Write-Host "=== Step 4/4: promotion candidate envelope ===" -ForegroundColor Cyan
$candidateOut = if ($TenantId -eq "contributor-community-v1") {
    "docs/final/artifacts/compression_contributor_promotion_candidate_v1_latest.json"
} else {
    "docs/final/artifacts/compression_contributor_promotion_candidate_${TenantId}_latest.json"
}
& py scripts/build_compression_contributor_promotion_candidate_v1.py `
    --validate-json $ValidateJson `
    --poc-json $PocJson `
    --tenant-id $TenantId `
    --out-json $candidateOut
$candidateExit = $LASTEXITCODE

Write-Host "" 
Write-Host "Next (commander only):" -ForegroundColor Green
Write-Host "  py scripts/apply_compression_contributor_track_a_promotion_v1.py --human-approve-promotion --reviewer commander"
Write-Host "Codec/active report (separate): apply_multilens_ultra_compression_track_a_promotion_v1.py --human-approve-promotion"

exit $candidateExit
