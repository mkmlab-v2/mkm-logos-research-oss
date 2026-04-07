# Local/staging verification: build (optional) -> validate JSON -> pytest -> optional deploy copy test.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File verify_showroom_bundle_chain.ps1
#   powershell ... -SkipBuild
#   powershell ... -WithStagingCopy

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipBuild,
    [switch]$WithStagingCopy
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$bundlePath = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"
$buildScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\build_showroom_display_bundle.ps1"
$validatePy = Join-Path $WorkspaceRoot "scripts\validate_showroom_public_bundle.py"
$qualityGatePy = Join-Path $WorkspaceRoot "scripts\verify_showroom_visual_quality_gate.py"
$featureContractPy = Join-Path $WorkspaceRoot "scripts\verify_showroom_feature_contracts.py"
$rollbackAtlasPy = Join-Path $WorkspaceRoot "scripts\rollback_showroom_atlas_pointer.py"
$gateLintPy = Join-Path $WorkspaceRoot "scripts\lint_jema12_terminology_gate.py"
$testPath = Join-Path $WorkspaceRoot "tests\test_validate_showroom_public_bundle.py"
$deployScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\deploy_showroom_static.ps1"
$stagingRoot = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\.showroom_staging"
$showroomRoot = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp"

if (-not $SkipBuild) {
    Write-Host "[verify-showroom] Step 1/7: build_showroom_display_bundle.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $buildScript -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "build failed" }
} else {
    Write-Host "[verify-showroom] Step 1/7: skipped (-SkipBuild)"
}

if (-not (Test-Path -LiteralPath $bundlePath)) {
    throw "[verify-showroom] missing $bundlePath (run without -SkipBuild)"
}

Write-Host "[verify-showroom] Step 2/7: validate_showroom_public_bundle.py"
py $validatePy $bundlePath
if ($LASTEXITCODE -ne 0) { throw "validate failed" }

Write-Host "[verify-showroom] Step 3/7: visual quality gate (atlas-only)"
py $qualityGatePy --game-root $showroomRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host "[verify-showroom] visual quality gate failed; attempting atlas pointer rollback"
    py $rollbackAtlasPy --game-root $showroomRoot --reason "verify_showroom_bundle_chain_quality_gate_failed"
    throw "visual quality gate failed"
}

Write-Host "[verify-showroom] Step 4/7: feature contracts"
py $featureContractPy --showroom-html (Join-Path $showroomRoot "public_showroom_poll.html")
if ($LASTEXITCODE -ne 0) { throw "feature contract failed" }

Write-Host "[verify-showroom] Step 5/7: Gate C terminology lint"
py $gateLintPy
if ($LASTEXITCODE -ne 0) { throw "Gate C lint failed" }

Write-Host "[verify-showroom] Step 6/7: pytest"
py -m pytest $testPath -q
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

if ($WithStagingCopy) {
    Write-Host "[verify-showroom] Step 7/7: deploy_showroom_static.ps1 (staging)"
    if (-not (Test-Path -LiteralPath $stagingRoot)) {
        New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null
    }
    powershell -NoProfile -ExecutionPolicy Bypass -File $deployScript -WebRoot $stagingRoot
    if ($LASTEXITCODE -ne 0) { throw "deploy staging failed" }
} else {
    Write-Host "[verify-showroom] Step 7/7: skipped (use -WithStagingCopy to test Copy-Item deploy)"
}

Write-Host "[verify-showroom] OK: bundle chain verified."
