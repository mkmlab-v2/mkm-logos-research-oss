# Track C public showroom: freshness sidecar -> showroom bundle -> validate (Fact-Lock).
# Does not scp/VPS — use scripts/sync_showroom_to_vps.ps1 -RefreshStaging after this, or deploy_showroom_static.ps1.
#
# Usage (repo root):
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/build_showroom_track_c_bundle_chain_v1.ps1
#   pwsh ... -SkipFreshnessSidecar   # only rebuild showroom JSON from current disk inputs
#   pwsh ... -SkipValidate          # skip validate_showroom_public_bundle.py

param(
    [string]$WorkspaceRoot = "",
    [switch]$SkipFreshnessSidecar,
    [switch]$SkipValidate
)

$ErrorActionPreference = "Stop"
$root = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $WorkspaceRoot
}
Set-Location -LiteralPath $root

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) {
    $py = "python"
}

Write-Host "=== build_showroom_track_c_bundle_chain_v1 (WorkspaceRoot=$root) ===" -ForegroundColor Cyan

if (-not $SkipFreshnessSidecar) {
    Write-Host "[chain] (1/3) logos_track_c_freshness_sidecar" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\build_logos_track_c_freshness_sidecar_v1.py")
    if ($LASTEXITCODE -ne 0) {
        Write-Error "build_logos_track_c_freshness_sidecar_v1.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (1/3) SKIP freshness sidecar" -ForegroundColor Yellow
}

$buildPs1 = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\build_showroom_display_bundle.ps1"
Write-Host "[chain] (2/3) build_showroom_display_bundle" -ForegroundColor Cyan
$psExe = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell.exe" }
& $psExe -NoProfile -ExecutionPolicy Bypass -File $buildPs1 -WorkspaceRoot $root
if ($LASTEXITCODE -ne 0) {
    Write-Error "build_showroom_display_bundle.ps1 failed: $LASTEXITCODE"
    exit $LASTEXITCODE
}

$bundleOut = Join-Path $root "docs\final\artifacts\showroom_public_bundle_v1.json"
if (-not $SkipValidate) {
    Write-Host "[chain] (3/3) validate_showroom_public_bundle" -ForegroundColor Cyan
    & $py (Join-Path $root "scripts\validate_showroom_public_bundle.py") $bundleOut
    if ($LASTEXITCODE -ne 0) {
        Write-Error "validate_showroom_public_bundle.py failed: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[chain] (3/3) SKIP validate" -ForegroundColor Yellow
}

Write-Host "[chain] OK -> $bundleOut" -ForegroundColor Green
exit 0
