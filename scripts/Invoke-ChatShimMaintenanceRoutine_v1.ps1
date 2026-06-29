# Chat shim dogfood maintenance — health, phase4, shadow, A/B bench, plan refresh (B-track)
param(
    [int]$ShimPort = 8011,
    [switch]$SkipAbBench,
    [switch]$SkipShadow,
    [switch]$StartShimIfDown
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Test-ShimHealth {
    param([int]$Port)
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        return ($h.status -eq "ok")
    }
    catch { return $false }
}

if (-not (Test-ShimHealth -Port $ShimPort)) {
    if ($StartShimIfDown) {
        Write-Host "[*] starting shim on :$ShimPort" -ForegroundColor Cyan
        Start-Process -FilePath "py" -ArgumentList "scripts/sandbox/launch_chat_shim_server_v1.py" -WorkingDirectory $Root -WindowStyle Minimized | Out-Null
        foreach ($i in 1..20) {
            Start-Sleep -Seconds 1
            if (Test-ShimHealth -Port $ShimPort) { break }
        }
    }
    if (-not (Test-ShimHealth -Port $ShimPort)) {
        Write-Host "SHIM_DOWN: py scripts/sandbox/launch_chat_shim_server_v1.py" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[1/4] phase4 dogfood probe" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LocalCursorChatShimPhase4Dogfood_v1.ps1 -SkipStart -ShimPort $ShimPort
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipShadow) {
    Write-Host "[2/4] upstream shadow" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LocalCursorChatShimUpstreamShadow_v1.ps1 -ReuseRunningShim -ShimPort $ShimPort
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host "[2/4] upstream shadow skipped" -ForegroundColor DarkGray
}

if (-not $SkipAbBench) {
    Write-Host "[3/4] compress A/B bench (n40)" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ChatShimCompressAbBench_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
else {
    Write-Host "[3/4] A/B bench skipped" -ForegroundColor DarkGray
}

Write-Host "[4/4] refresh chat shim plan" -ForegroundColor Cyan
py scripts/build_local_cursor_chat_shim_v1.py --write-plan
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Chat shim maintenance OK" -ForegroundColor Green
exit 0
