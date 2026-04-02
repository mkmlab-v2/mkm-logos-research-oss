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
$testPath = Join-Path $WorkspaceRoot "tests\test_validate_showroom_public_bundle.py"
$deployScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\deploy_showroom_static.ps1"
$stagingRoot = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\.showroom_staging"

if (-not $SkipBuild) {
    Write-Host "[verify-showroom] Step 1/4: build_showroom_display_bundle.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $buildScript -WorkspaceRoot $WorkspaceRoot
    if ($LASTEXITCODE -ne 0) { throw "build failed" }
} else {
    Write-Host "[verify-showroom] Step 1/4: skipped (-SkipBuild)"
}

if (-not (Test-Path -LiteralPath $bundlePath)) {
    throw "[verify-showroom] missing $bundlePath (run without -SkipBuild)"
}

Write-Host "[verify-showroom] Step 2/4: validate_showroom_public_bundle.py"
py $validatePy $bundlePath
if ($LASTEXITCODE -ne 0) { throw "validate failed" }

Write-Host "[verify-showroom] Step 3/4: pytest"
py -m pytest $testPath -q
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

if ($WithStagingCopy) {
    Write-Host "[verify-showroom] Step 4/4: deploy_showroom_static.ps1 (staging)"
    if (-not (Test-Path -LiteralPath $stagingRoot)) {
        New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null
    }
    powershell -NoProfile -ExecutionPolicy Bypass -File $deployScript -WebRoot $stagingRoot
    if ($LASTEXITCODE -ne 0) { throw "deploy staging failed" }
} else {
    Write-Host "[verify-showroom] Step 4/4: skipped (use -WithStagingCopy to test Copy-Item deploy)"
}

Write-Host "[verify-showroom] OK: bundle chain verified."
