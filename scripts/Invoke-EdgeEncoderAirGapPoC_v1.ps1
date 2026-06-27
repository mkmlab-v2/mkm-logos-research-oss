# Edge Encoder air-gap PoC chain — pack + bundle + verify + HTTP + PyInstaller + VPC runbook [HYPO] B-track.
param(
    [switch]$SkipBundle,
    [switch]$SkipVerify,
    [switch]$SkipCrossProcess
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "[1/9] build portable SDK launchers"
py scripts/build_edge_encoder_sdk_portable_launcher_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/9] build air-gap PoC pack metadata"
py scripts/build_edge_encoder_air_gap_poc_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipBundle) {
    Write-Host "[3/9] materialize offline bundle"
    py scripts/build_edge_encoder_air_gap_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[3/9] skip bundle materialize"
}

if (-not $SkipVerify) {
    Write-Host "[4/9] verify bundle integrity + local roundtrip"
    py scripts/check_edge_encoder_air_gap_bundle_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[4/9] skip bundle verify"
}

if (-not $SkipCrossProcess) {
    Write-Host "[5/9] cross-process HTTP determinism (ephemeral uvicorn)"
    py scripts/check_edge_encoder_cross_process_determinism_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[5/9] skip cross-process HTTP gate"
}

Write-Host "[6/9] SDK smoke"
py scripts/run_edge_encoder_sdk_cli_v1.py smoke
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[7/9] PyInstaller spec + readiness"
py scripts/build_edge_encoder_sdk_pyinstaller_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/check_edge_encoder_pyinstaller_readiness_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[8/9] VPC deploy runbook artifact"
py scripts/build_edge_encoder_vpc_deploy_runbook_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[9/9] VPC operator HTML checklist"
py scripts/build_edge_encoder_vpc_checklist_html_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/check_edge_encoder_pyinstaller_binary_smoke_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[10/10] VPC deploy package zip (bundle + exe + checklist)"
py scripts/build_edge_encoder_vpc_deploy_package_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: Edge Encoder air-gap PoC chain complete"
