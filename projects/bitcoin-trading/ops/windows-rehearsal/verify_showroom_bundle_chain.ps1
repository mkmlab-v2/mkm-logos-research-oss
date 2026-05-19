# Local/staging verification: Track C chain (optional: freshness+build+validate) -> quality gates -> pytest -> optional deploy copy.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File verify_showroom_bundle_chain.ps1
#   powershell ... -SkipBuild
#   powershell ... -WithStagingCopy
#   powershell ... -SkipFreshnessInBuild  # pass -SkipFreshnessSidecar to the chain

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipBuild,
    [switch]$WithStagingCopy,
    [switch]$SkipVisualQualityGate,
    # Passed through to build_showroom_track_c_bundle_chain_v1.ps1 when building
    [switch]$SkipFreshnessInBuild
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

$bundlePath = Join-Path $WorkspaceRoot "docs\final\artifacts\showroom_public_bundle_v1.json"
$trackCChain = Join-Path $WorkspaceRoot "scripts\build_showroom_track_c_bundle_chain_v1.ps1"
$qualityGatePy = Join-Path $WorkspaceRoot "scripts\verify_showroom_visual_quality_gate.py"
$featureContractPy = Join-Path $WorkspaceRoot "scripts\verify_showroom_feature_contracts.py"
$rollbackAtlasPy = Join-Path $WorkspaceRoot "scripts\rollback_showroom_atlas_pointer.py"
$gateLintPy = Join-Path $WorkspaceRoot "scripts\lint_jema12_terminology_gate.py"
$testPath = Join-Path $WorkspaceRoot "tests\test_validate_showroom_public_bundle.py"
$deployScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\deploy_showroom_static.ps1"
$stagingRoot = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\.showroom_staging"
$showroomRoot = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp"

if (-not $SkipBuild) {
    $psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
    $chainLabel = if ($SkipFreshnessInBuild) {
        "build_showroom_track_c_bundle_chain_v1.ps1 -SkipFreshnessSidecar"
    } else {
        "build_showroom_track_c_bundle_chain_v1.ps1"
    }
    Write-Host "[verify-showroom] Step 1/6: $chainLabel"
    if ($SkipFreshnessInBuild) {
        & $psExe -NoProfile -ExecutionPolicy Bypass -File $trackCChain -WorkspaceRoot $WorkspaceRoot -SkipFreshnessSidecar
    } else {
        & $psExe -NoProfile -ExecutionPolicy Bypass -File $trackCChain -WorkspaceRoot $WorkspaceRoot
    }
    if ($LASTEXITCODE -ne 0) { throw "Track C showroom chain failed" }
} else {
    Write-Host "[verify-showroom] Step 1/6: skipped (-SkipBuild)"
}

if (-not (Test-Path -LiteralPath $bundlePath)) {
    throw "[verify-showroom] missing $bundlePath (run without -SkipBuild)"
}

if ($SkipVisualQualityGate) {
    Write-Host "[verify-showroom] Step 2/6: skipped (-SkipVisualQualityGate; atlas/WebGL poll not required for topology graph B2B)"
} else {
    Write-Host "[verify-showroom] Step 2/6: visual quality gate (atlas-only)"
    py $qualityGatePy --game-root $showroomRoot
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $rollbackAtlasPy) {
            Write-Host "[verify-showroom] visual quality gate failed; attempting atlas pointer rollback"
            py $rollbackAtlasPy --game-root $showroomRoot --reason "verify_showroom_bundle_chain_quality_gate_failed"
        } else {
            Write-Host "[verify-showroom] visual quality gate failed; rollback script not present: $rollbackAtlasPy" -ForegroundColor Yellow
        }
        throw "visual quality gate failed"
    }
}

Write-Host "[verify-showroom] Step 3/6: feature contracts"
py $featureContractPy --showroom-html (Join-Path $showroomRoot "public_showroom_poll.html")
if ($LASTEXITCODE -ne 0) { throw "feature contract failed" }

if (Test-Path -LiteralPath $gateLintPy) {
    Write-Host "[verify-showroom] Step 4/6: Gate C terminology lint"
    py $gateLintPy
    if ($LASTEXITCODE -ne 0) { throw "Gate C lint failed" }
} else {
    Write-Host "[verify-showroom] Step 4/6: skipped (missing $gateLintPy)"
}

Write-Host "[verify-showroom] Step 5/6: pytest"
py -m pytest $testPath -q
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

if ($WithStagingCopy) {
    Write-Host "[verify-showroom] Step 6/6: deploy_showroom_static.ps1 (staging)"
    if (-not (Test-Path -LiteralPath $stagingRoot)) {
        New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null
    }
    powershell -NoProfile -ExecutionPolicy Bypass -File $deployScript -WebRoot $stagingRoot
    if ($LASTEXITCODE -ne 0) { throw "deploy staging failed" }
} else {
    Write-Host "[verify-showroom] Step 6/6: skipped (use -WithStagingCopy to test Copy-Item deploy)"
}

Write-Host "[verify-showroom] OK: bundle chain verified."
