# Trust Composition — design lane auto (local gates + optional live wedge smoke + clinic LOI full).
param(
    [switch]$SkipLiveSmoke,
    [switch]$SkipClinicLoiFull,
    [switch]$FetchFigma,
    [switch]$IncludeMagicOrbChain,
    [switch]$SkipPytest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [1/4] trust composition rollout ===" -ForegroundColor Cyan
$rollArgs = @('-File', 'scripts/Run-TrustCompositionRolloutPriorities_v1.ps1')
if ($IncludeMagicOrbChain) { $rollArgs += '-IncludeMagicOrbChain' }
& powershell -NoProfile -ExecutionPolicy Bypass @rollArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipClinicLoiFull) {
    Write-Host "`n=== [2/4] clinic LOI full readiness ===" -ForegroundColor Cyan
    $clinicArgs = @('-File', 'scripts/Run-TrustCompositionClinicLoiFull_v1.ps1')
    if ($FetchFigma) { $clinicArgs += '-FetchFigma' }
    if ($SkipPytest) { $clinicArgs += '-SkipPytest' }
    & powershell -NoProfile -ExecutionPolicy Bypass @clinicArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "`n=== [2/4] clinic LOI full SKIPPED ===" -ForegroundColor Yellow
}

Write-Host "`n=== [3/4] ops sync bridge domain adapters ===" -ForegroundColor Cyan
& py scripts/check_mkm_ops_sync_bridge_domain_adapters_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipLiveSmoke) {
    Write-Host "`n=== [4/4] trust wedge live smoke (non-fatal on fail) ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-TrustCompositionTrustWedgeLiveSmoke_v1.ps1
    $liveEc = $LASTEXITCODE
    if ($liveEc -ne 0) {
        Write-Host "WARN: live trust wedge smoke failed (deploy may be pending) exit=$liveEc" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n=== [4/4] live smoke SKIPPED ===" -ForegroundColor Yellow
}

Write-Host "`nOK: Trust Composition design lane auto completed." -ForegroundColor Green
exit 0
