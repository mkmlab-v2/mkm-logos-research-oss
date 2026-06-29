# Public-open web corpus fetch -> bootstrap -> routed pilot ROI (NOT customer case study).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "public-open-web-v1",
    [int]$MaxCases = 30,
    [string]$Sku = "MKM-CHAT-D1",
    [ValidateSet("economy", "fidelity", "literal")]
    [string]$CompressionProfile = "economy",
    [switch]$RelaxPassGate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$PublicJsonl = "data/compression/stateless_poc_public_open_web_v1.jsonl"

Write-Host "=== Public-open pilot intake (API/RSS) ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | NOT customer corpus | SEND_GATE HOLD" -ForegroundColor Yellow

if ($DryRun) {
    & py scripts/fetch_compression_pilot_public_corpus_v1.py --max-cases $MaxCases --dry-run
    exit $LASTEXITCODE
}

Write-Host "=== Step 1/3: fetch public corpus ===" -ForegroundColor Cyan
& py scripts/fetch_compression_pilot_public_corpus_v1.py --max-cases $MaxCases --out-jsonl $PublicJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 2/3: bootstrap tenant from public JSONL ===" -ForegroundColor Cyan
& py scripts/bootstrap_compression_pilot_tenant_v1.py --tenant-id $TenantId --source-jsonl $PublicJsonl --max-cases $MaxCases
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 3/3: routed pilot chain ===" -ForegroundColor Cyan
$pilotArgs = @(
    "scripts/Run-CompressionPilotIntakeBlueprint_v1.ps1",
    "-TenantId", $TenantId,
    "-MaxCases", "$MaxCases",
    "-Sku", $Sku,
    "-CompressionProfile", $CompressionProfile,
    "-SkipProofCompletion"
)
if ($RelaxPassGate) { $pilotArgs += "-RelaxPassGate" }
& powershell -NoProfile -ExecutionPolicy Bypass -File @pilotArgs
exit $LASTEXITCODE
