# Edge Encoder air-gap PoC chain — pack + bundle + verify + SDK smoke [HYPO] B-track.
param(
    [switch]$SkipBundle,
    [switch]$SkipVerify
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "[1/4] build air-gap PoC pack metadata"
py scripts/build_edge_encoder_air_gap_poc_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipBundle) {
    Write-Host "[2/4] materialize offline bundle"
    py scripts/build_edge_encoder_air_gap_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[2/4] skip bundle materialize"
}

if (-not $SkipVerify) {
    Write-Host "[3/4] verify bundle integrity + local roundtrip"
    py scripts/check_edge_encoder_air_gap_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[3/4] skip bundle verify"
}

Write-Host "[4/4] SDK smoke"
py scripts/run_edge_encoder_sdk_cli_v1.py smoke
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: Edge Encoder air-gap PoC chain complete"
