# Contributor prophecy JSONL -> validate -> sandbox registry -> Brier eval -> promotion candidate (B-track).
param(
    [Parameter(Mandatory = $true)]
    [string]$ContributorJsonl,
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "prophecy-contributor-community-v1",
    [int]$MinRows = 5,
    [switch]$DryRun
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

Write-Host "=== Prophecy contributor bench chain (B-track) ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | SEND_GATE HOLD | no auto registry merge" -ForegroundColor Yellow
Write-Host "kit: docs/final/artifacts/prophecy_open_bench_contributor_kit_v1_latest.json" -ForegroundColor DarkGray

if ($DryRun) {
    Write-Host "[DryRun] validate -> sandbox -> brier -> candidate" -ForegroundColor DarkGray
    exit 0
}

$ValidateJson = "reports/prophecy_contributor_jsonl_validate_${TenantId}_latest.json"
$SandboxJson = "reports/prophecy_contributor_sandbox_registry_v1_latest.json"
$BrierJson = "reports/prophecy_contributor_brier_eval_v1_latest.json"

Write-Host "=== Step 1/4: validate contributor JSONL ===" -ForegroundColor Cyan
& py scripts/validate_prophecy_contributor_jsonl_v1.py --jsonl $JsonlPath --min-rows $MinRows --out-json $ValidateJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 2/4: sandbox registry (not general_prophecy_latest) ===" -ForegroundColor Cyan
& py scripts/build_prophecy_contributor_sandbox_registry_v1.py --jsonl $JsonlPath --tenant-id $TenantId --out-json $SandboxJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 3/4: Brier eval on sandbox (resolved rows only) ===" -ForegroundColor Cyan
& py scripts/eval_general_prophecy_brier_score.py --input $SandboxJson --output $BrierJson
$brierExit = $LASTEXITCODE
if ($brierExit -ne 0) {
    Write-Host "Brier eval exit $brierExit (pending-only corpus may be OK)" -ForegroundColor Yellow
}

Write-Host "=== Step 4/4: promotion candidate envelope ===" -ForegroundColor Cyan
$candidateOut = if ($TenantId -eq "prophecy-contributor-community-v1") {
    "docs/final/artifacts/prophecy_contributor_promotion_candidate_v1_latest.json"
} else {
    "docs/final/artifacts/prophecy_contributor_promotion_candidate_${TenantId}_latest.json"
}
& py scripts/build_prophecy_contributor_promotion_candidate_v1.py --validate-json $ValidateJson --sandbox-registry-json $SandboxJson --brier-eval-json $BrierJson --tenant-id $TenantId --out-json $candidateOut
$candidateExit = $LASTEXITCODE

Write-Host ""
Write-Host "Next (commander only):" -ForegroundColor Green
Write-Host "  py scripts/apply_prophecy_contributor_promotion_v1.py --human-approve-promotion --reviewer commander"

exit $candidateExit
