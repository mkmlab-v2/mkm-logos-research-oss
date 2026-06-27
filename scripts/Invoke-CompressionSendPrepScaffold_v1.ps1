#Requires -Version 5.1
<#
.SYNOPSIS
  SEND prep scaffold: validate intake kit + masked JSONL stub; optional stub rehearsal.

  Synthetic stub only — not customer data. SEND_GATE stays HOLD until real masked JSONL + counsel.

.EXAMPLE
  pwsh -NoProfile -File scripts/Invoke-CompressionSendPrepScaffold_v1.ps1

.EXAMPLE
  pwsh -NoProfile -File scripts/Invoke-CompressionSendPrepScaffold_v1.ps1 -RunStubRehearsal -RelaxPassGate
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$StubJsonl = "data/compression/pilot_masked_customer_stub_v1.example.jsonl",
    [string]$StubTenantId = "pilot-masked-stub-v1",
    [int]$MinCases = 20,
    [switch]$RunStubRehearsal,
    [switch]$RelaxPassGate,
    [switch]$BuildCounselEnvelope
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$kit = Join-Path $WorkspaceRoot "docs/final/artifacts/compression_pilot_target_intake_kit_v1_latest.json"
$stubPath = if ([System.IO.Path]::IsPathRooted($StubJsonl)) {
    (Resolve-Path -LiteralPath $StubJsonl).Path
} else {
    (Resolve-Path -LiteralPath (Join-Path $WorkspaceRoot $StubJsonl)).Path
}

if (-not (Test-Path -LiteralPath $kit)) {
    Write-Error "Intake kit missing: $kit"
}
if (-not (Test-Path -LiteralPath $stubPath)) {
    Write-Error "Stub JSONL missing: $stubPath"
}

$rows = @(Get-Content -LiteralPath $stubPath | Where-Object { $_.Trim() -ne "" })
if ($rows.Count -lt $MinCases) {
    Write-Error "Stub JSONL has $($rows.Count) rows; need >= $MinCases"
}

Write-Host "=== SEND prep scaffold (HOLD) ===" -ForegroundColor Cyan
Write-Host "kit: $kit" -ForegroundColor DarkGray
Write-Host "stub: $stubPath ($($rows.Count) rows)" -ForegroundColor DarkGray
Write-Host "send_gate: HOLD | ready_for_external_send: false" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next (human):" -ForegroundColor Yellow
Write-Host "  1. Receive 20-50 customer-masked JSONL (local path; do not commit raw logs)"
Write-Host "  2. Run-CompressionCustomerPilotIntake_v1.ps1 -TenantId <slug> -CustomerJsonl <path>"
Write-Host "  3. apply_compression_b2b_legal_send_signoff_v1.py --counsel-acknowledge (after counsel)"
Write-Host ""

if ($BuildCounselEnvelope) {
    Write-Host "=== Counsel envelope (SEND prep · HOLD) ===" -ForegroundColor Cyan
    py scripts/build_compression_b2b_send_prep_counsel_envelope_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/build_compression_b2b_counsel_export_manifest_v1.py --fail-if-missing
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/build_compression_b2b_counsel_zip_pack_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[OK] counsel envelope zip ready (send_gate still HOLD)" -ForegroundColor Green
}

if (-not $RunStubRehearsal) {
    Write-Host "[OK] validate-only complete" -ForegroundColor Green
    exit 0
}

Write-Host "=== Stub rehearsal (synthetic — not customer ROI claim) ===" -ForegroundColor Cyan
$pilotArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $WorkspaceRoot "scripts\Run-CompressionCustomerPilotIntake_v1.ps1"),
    "-TenantId", $StubTenantId,
    "-CustomerJsonl", $stubPath,
    "-MaxCases", "25"
)
if ($RelaxPassGate) { $pilotArgs += "-RelaxPassGate" }
& powershell @pilotArgs
exit $LASTEXITCODE
