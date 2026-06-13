# Compression B2B pilot intake — routed SKU + tenant must_keep + dollar ROI.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "prospect-first-pilot-v1",
    [int]$MaxCases = 30,
    [string]$Sku = "MKM-CHAT-D1",
    [ValidateSet("economy", "fidelity", "literal")]
    [string]$CompressionProfile = "economy",
    [switch]$IncludeCalibration,
    [switch]$RelaxPassGate,
    [switch]$StrictPassGate,
    [switch]$SkipProofCompletion,
    [switch]$DryRun,
    [switch]$BtrackCsShortContext,
    [switch]$StripRolePrefixes,
    [switch]$SkipMustKeepExtract,
    [int]$ShortContextTokenThreshold = 30,
    [double]$ShortContextMaxSavingRate = 0.30
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$CorpusRel = "data/compression/stateless_poc_prospect_${TenantId}_v1.jsonl"
$IntakeRel = "reports/compression_b2b_prospect_poc_corpus_${TenantId}_v1.json"
$OverlayRel = "docs/final/artifacts/tenant_${TenantId}_must_keep_overlay_v1.json"
$CorpusPath = Join-Path $WorkspaceRoot $CorpusRel
$IntakePath = Join-Path $WorkspaceRoot $IntakeRel

Write-Host "=== Compression pilot intake (routed) ===" -ForegroundColor Cyan
Write-Host "tenant_id: $TenantId | sku: $Sku | profile: $CompressionProfile"
if ($BtrackCsShortContext) {
    Write-Host "btrack_cs_shortcontext: [HYPO] cap=$ShortContextMaxSavingRate @<=$ShortContextTokenThreshold tok" -ForegroundColor DarkYellow
}
Write-Host "send_gate: HOLD" -ForegroundColor Yellow

if (-not (Test-Path -LiteralPath $CorpusPath) -or -not (Test-Path -LiteralPath $IntakePath)) {
    Write-Host "=== Bootstrap: tenant corpus + intake ===" -ForegroundColor Cyan
    & py scripts/bootstrap_compression_pilot_tenant_v1.py --tenant-id $TenantId --max-cases $MaxCases
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    $existingRows = (Get-Content -LiteralPath $CorpusPath | Where-Object { $_.Trim() -ne "" }).Count
    if ($existingRows -lt $MaxCases) {
        Write-Host "=== Refresh corpus ($existingRows -> $MaxCases rows) ===" -ForegroundColor Cyan
        $bootstrapArgs = @(
            "scripts/bootstrap_compression_pilot_tenant_v1.py",
            "--tenant-id", $TenantId,
            "--max-cases", "$MaxCases"
        )
        if (Test-Path -LiteralPath $IntakePath) {
            try {
                $intakeDoc = Get-Content -LiteralPath $IntakePath -Raw | ConvertFrom-Json
                $customerSrc = $intakeDoc.customer_source_jsonl
                if ($customerSrc) {
                    $bootstrapArgs += @("--customer-masked", "--source-jsonl", "$customerSrc")
                } elseif ($intakeDoc.corpus_provenance -eq "customer_masked_jsonl_v1") {
                    Write-Host "WARN: customer_masked provenance without customer_source_jsonl — refresh skipped" -ForegroundColor Yellow
                    $bootstrapArgs = $null
                }
            } catch {
                Write-Host "WARN: intake JSON parse failed; golden40 refresh fallback" -ForegroundColor Yellow
            }
        }
        if ($bootstrapArgs) {
            & py @bootstrapArgs
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
    }
}

if ($DryRun) {
    Write-Host "[DryRun] extract -> routed poc -> dollar ROI" -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== Step 1/5: must_keep overlay extract ===" -ForegroundColor Cyan
$skipExtract = $SkipMustKeepExtract
if (-not $skipExtract -and (Test-Path -LiteralPath (Join-Path $WorkspaceRoot $OverlayRel))) {
    try {
        $overlayDoc = Get-Content -LiteralPath (Join-Path $WorkspaceRoot $OverlayRel) -Raw | ConvertFrom-Json
        $labels = @($overlayDoc.labels)
        if ($labels -contains "overlay_v2_cs_anchors" -or ($overlayDoc.extraction_stats.manual_cs_anchor_v2 -eq $true)) {
            $skipExtract = $true
            Write-Host "skip: manual CS overlay v2 preserved ($OverlayRel)" -ForegroundColor DarkYellow
        }
    } catch {
        Write-Host "WARN: overlay JSON parse failed; running extract" -ForegroundColor Yellow
    }
}
if (-not $skipExtract) {
    & py scripts/extract_tenant_must_keep_from_corpus_v1.py --tenant-id $TenantId --input-jsonl $CorpusRel
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[skip] must_keep extract (manual overlay or -SkipMustKeepExtract)" -ForegroundColor DarkGray
}

$useRelaxPassGate = $RelaxPassGate
if (-not $StrictPassGate -and -not $useRelaxPassGate -and (Test-Path -LiteralPath $IntakePath)) {
    try {
        $intakeForRelax = Get-Content -LiteralPath $IntakePath -Raw | ConvertFrom-Json
        if (
            $intakeForRelax.corpus_provenance -eq "customer_masked_jsonl_v1" -or
            $intakeForRelax.customer_source_jsonl
        ) {
            $useRelaxPassGate = $true
        }
    } catch {
        Write-Host "WARN: intake JSON parse failed; strict pass gate unchanged" -ForegroundColor Yellow
    }
}

Write-Host "=== Step 2/5: pilot ROI chain (routed) ===" -ForegroundColor Cyan
$pilotArgs = @(
    "scripts/run_compression_pilot_roi_chain_v1.py",
    "--tenant-id", $TenantId,
    "--input-jsonl", $CorpusRel,
    "--max-cases", "$MaxCases",
    "--sku", $Sku,
    "--compression-profile", $CompressionProfile
)
if ($useRelaxPassGate) { $pilotArgs += "--relax-pass-gate" }
if ($IncludeCalibration) { $pilotArgs += "--include-calibration" }
if ($BtrackCsShortContext) {
    $pilotArgs += @(
        "--short-context-token-threshold", "$ShortContextTokenThreshold",
        "--short-context-max-saving-rate", "$ShortContextMaxSavingRate"
    )
}
& py @pilotArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 3/5: customer dollar/KRW ROI receipt ===" -ForegroundColor Cyan
$pocJson = Join-Path $WorkspaceRoot "reports/customer_compression_stateless_poc_${TenantId}_v1_latest.json"
$meterJson = Join-Path $WorkspaceRoot "docs/final/artifacts/compression_b2b_pilot_metering_appendix_${TenantId}_latest.json"
& py scripts/build_compression_pilot_dollar_roi_v1.py `
    --tenant-id $TenantId `
    --poc-json $pocJson `
    --metering-appendix-json $meterJson `
    --intake-json $IntakePath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipProofCompletion) {
    Write-Host "=== Step 4/5: proof completion (skip re-poc if needed later) ===" -ForegroundColor Cyan
    & py scripts/run_compression_proof_completion_chain_v1.py --tenant-id $TenantId --skip-evidence
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "proof_completion_chain non-zero — continuing."
    }
    Write-Host "=== Step 5/5: refresh dollar ROI after proof chain ===" -ForegroundColor Cyan
    & py scripts/build_compression_pilot_dollar_roi_v1.py `
        --tenant-id $TenantId `
        --poc-json $pocJson `
        --metering-appendix-json $meterJson `
        --intake-json $IntakePath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "OK: Routed pilot complete for '$TenantId'." -ForegroundColor Green
Write-Host "  poc:  reports/customer_compression_stateless_poc_${TenantId}_v1_latest.json"
Write-Host "  roi:  docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"
