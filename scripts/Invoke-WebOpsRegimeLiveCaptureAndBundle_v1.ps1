#Requires -Version 5.1
<#
.SYNOPSIS
  Start CDP Chrome if needed, capture live observation, run web_ops_regime full bundle.

.EXAMPLE
  pwsh -File scripts/Invoke-WebOpsRegimeLiveCaptureAndBundle_v1.ps1
  pwsh -File scripts/Invoke-WebOpsRegimeLiveCaptureAndBundle_v1.ps1 -SkipChromeStart
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$CdpUrl = "http://127.0.0.1:9222",
    [string]$HostFilter = "console.nebius.com",
    [switch]$SkipChromeStart,
    [switch]$SkipCapture,
    [switch]$NoSeedBaselines
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

function Test-CdpUp([string]$Url) {
    try {
        $null = Invoke-WebRequest -Uri "$Url/json/version" -UseBasicParsing -TimeoutSec 3
        return $true
    } catch {
        return $false
    }
}

if (-not $SkipChromeStart -and -not (Test-CdpUp $CdpUrl)) {
    $starter = Join-Path $WorkspaceRoot "scripts\Start-ChromeForNvidiaInceptionCdp_v1.ps1"
    if (Test-Path -LiteralPath $starter) {
        Write-Host "[web_ops] CDP down — starting Chrome..." -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $starter
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Start-Sleep -Seconds 2
    }
}

if (-not $SkipCapture) {
    if (Test-CdpUp $CdpUrl) {
        Write-Host "[web_ops] Capturing live observation via CDP..." -ForegroundColor Cyan
        & py (Join-Path $WorkspaceRoot "scripts\capture_web_ops_regime_cdp_observation_v1.py") `
            --cdp-url $CdpUrl --host-filter $HostFilter `
            --open-url "https://console.nebius.com/tenant-e00fe2zhs67gmz6wha/billing/payments"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[web_ops] CDP capture failed — bundle will use stored observation/portal fallback." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[web_ops] CDP still down — skip capture; using stored observation/portal fallback." -ForegroundColor Yellow
    }
}

$bundleArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $WorkspaceRoot "scripts\Run-WebOpsRegimeFullBundle_v1.ps1"),
    "--require-dual-alignment"
)
if ($NoSeedBaselines) { $bundleArgs += "--no-seed-baselines" }

& powershell @bundleArgs
$bundleRc = $LASTEXITCODE

& py (Join-Path $WorkspaceRoot "scripts\build_web_ops_regime_health_summary_v1.py") --require-health-ok
$summaryRc = $LASTEXITCODE

if ($bundleRc -ne 0) { exit $bundleRc }
exit $summaryRc
