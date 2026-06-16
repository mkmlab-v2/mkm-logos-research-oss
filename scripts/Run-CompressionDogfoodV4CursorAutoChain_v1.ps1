# Auto chain runner: v4 cursor one-click + status artifact.
# B-track research_only. SEND_GATE remains HOLD.

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "mkm-internal-dogfood-v4-cursor",
    [int]$Rows = 24,
    [int]$MaxCases = 24
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$timestamp = (Get-Date).ToUniversalTime().ToString("o")
$statusPath = Join-Path $WorkspaceRoot "reports\compression_dogfood_v4_cursor_auto_chain_latest.json"

Write-Host "=== Compression Dogfood V4 Cursor Auto Chain ===" -ForegroundColor Cyan

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CompressionDogfoodV4CursorOneClick_v1.ps1 `
    -WorkspaceRoot $WorkspaceRoot `
    -TenantId $TenantId `
    -Rows $Rows `
    -MaxCases $MaxCases

$exitCode = $LASTEXITCODE

$out = [ordered]@{
    schema = "compression_dogfood_v4_cursor_auto_chain_status_v1"
    generated_at_utc = $timestamp
    ok = ($exitCode -eq 0)
    exit_code = $exitCode
    tenant_id = $TenantId
    rows = $Rows
    max_cases = $MaxCases
    runner = "scripts/Run-CompressionDogfoodV4CursorAutoChain_v1.ps1"
    invoke = "scripts/Invoke-CompressionDogfoodV4CursorOneClick_v1.ps1"
    artifacts = @(
        "data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl",
        "reports/customer_compression_stateless_poc_mkm-internal-dogfood-v4-cursor_v1_latest.json",
        "docs/final/artifacts/compression_dogfood_briefing_v1_latest.json"
    )
    send_gate_expected = "HOLD"
    research_only = $true
}

$outDir = Split-Path -Parent $statusPath
if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$out | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Host "status: $statusPath" -ForegroundColor Green

exit $exitCode

