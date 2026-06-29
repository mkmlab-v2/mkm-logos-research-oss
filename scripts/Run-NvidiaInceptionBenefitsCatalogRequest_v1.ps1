# Request Inception benefits catalog (AWS/GCP/Lambda…) — skips Innovation Lab.
# Uses system Google Chrome + CDP (NOT Playwright persistent profile — avoids exit 2147483651).

param(
    [string[]]$Targets = @()
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$cdp = 'http://127.0.0.1:9222'
$waitSec = 300

function Test-CdpUp {
    try {
        $null = Invoke-WebRequest -Uri "$cdp/json/version" -UseBasicParsing -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-CdpUp)) {
    Write-Host "[info] Starting Google Chrome CDP (Start-ChromeForNvidiaInceptionCdp_v1.ps1)..." -ForegroundColor Cyan
    & "$root\scripts\Start-ChromeForNvidiaInceptionCdp_v1.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not (Test-CdpUp)) {
    Write-Host "[fail] CDP still down. Close all Chrome, re-run this script, log in when Chrome opens." -ForegroundColor Yellow
    exit 1
}

Write-Host "[info] CDP attach — log in to NVIDIA in the Chrome window if needed (pop-ups ON)." -ForegroundColor Cyan
# PowerShell: '$7' in targets must use single-quoted -Targets or py gets ",500..."
$pyArgs = @(
    'scripts/nvidia_inception_benefits_catalog_request_v1.py',
    '--cdp-url', $cdp,
    '--wait-for-login-sec', "$waitSec"
)
if ($Targets -and $Targets.Count -gt 0) {
    $pyArgs += '--targets'
    $pyArgs += $Targets
}
py @pyArgs
exit $LASTEXITCODE
