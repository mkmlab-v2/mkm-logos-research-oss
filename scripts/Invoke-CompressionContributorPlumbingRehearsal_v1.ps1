# Gate-plumbing E2E: build rehearsal corpus -> bench chain -> candidate (rehearsal) -> apply --dry-run.
# Does NOT modify compression_contributor_example_v1.jsonl (deny-valve SSOT).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "contributor-plumbing-rehearsal-v1",
    [int]$Rows = 12,
    [ValidateSet("economy", "fidelity", "literal")]
    [string]$CompressionProfile = "fidelity",
    [switch]$SkipApplyDryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$RehearsalJsonl = "data/compression/examples/compression_contributor_gate_plumbing_rehearsal_v1.jsonl"
$CandidateJson = "docs/final/artifacts/compression_contributor_promotion_candidate_plumbing_rehearsal_v1_latest.json"

Write-Host "=== Contributor gate-plumbing rehearsal (B-track; NOT Moat SSOT) ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | rehearsal_only | SEND_GATE HOLD" -ForegroundColor Yellow

Write-Host "=== Step 0/5: build rehearsal corpus ===" -ForegroundColor Cyan
& py scripts/build_compression_contributor_gate_plumbing_rehearsal_corpus_v1.py `
    --out-jsonl $RehearsalJsonl `
    --rows $Rows
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Steps 1-4/5: validate -> bootstrap -> PoC -> candidate ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CompressionContributorBenchChain_v1.ps1 `
    -ContributorJsonl $RehearsalJsonl `
    -TenantId $TenantId `
    -MaxCases $Rows `
    -MinRows 10 `
    -CompressionProfile $CompressionProfile `
    -RelaxPassGate
$chainExit = $LASTEXITCODE

# Rebuild candidate with rehearsal flag + isolated artifact path (chain wrote default path).
$ValidateJson = "reports/compression_contributor_jsonl_validate_${TenantId}_latest.json"
& py scripts/build_compression_contributor_promotion_candidate_v1.py `
    --validate-json $ValidateJson `
    --poc-json "reports/customer_compression_stateless_poc_$TenantId`_v1_latest.json" `
    --tenant-id $TenantId `
    --out-json $CandidateJson `
    --rehearsal-only
$candidateExit = $LASTEXITCODE

if (-not $SkipApplyDryRun) {
    Write-Host "=== Step 5/5: apply bridge --dry-run (commander rehearsal) ===" -ForegroundColor Cyan
    if ($candidateExit -eq 0) {
        & py scripts/apply_compression_contributor_track_a_promotion_v1.py `
            --human-approve-promotion `
            --reviewer commander `
            --note "gate_plumbing_rehearsal_dry_run" `
            --candidate-json $CandidateJson `
            --signoff-json docs/final/artifacts/compression_contributor_track_a_signoff_plumbing_rehearsal_v1_latest.json `
            --evidence-json docs/final/artifacts/compression_contributor_track_a_evidence_plumbing_rehearsal_v1_latest.json `
            --dry-run
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "Skip apply dry-run: promotion gates not met (expected for deny-valve demo on short example only)." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Artifacts:" -ForegroundColor Green
Write-Host "  corpus: $RehearsalJsonl"
Write-Host "  candidate: $CandidateJson"
Write-Host "  canonical deny-valve example unchanged: data/compression/examples/compression_contributor_example_v1.jsonl"

exit $candidateExit
