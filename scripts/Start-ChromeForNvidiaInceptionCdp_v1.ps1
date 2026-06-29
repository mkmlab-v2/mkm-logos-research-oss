#Requires -Version 5.1
<#
.SYNOPSIS
  NVIDIA Inception / Benefits — system Google Chrome + CDP (not Playwright bundled Chromium).
  Avoids launch_persistent_context profile lock (exit 2147483651).
#>
$ErrorActionPreference = "Stop"
$cdpPort = 9222
$profile = Join-Path $env:LOCALAPPDATA "NvidiaInceptionAutofillChrome"
$startUrl = "https://programs.nvidia.com/phoenix/benefits"

$chromeCandidates = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chrome) {
    Write-Error "Google Chrome not found"
}

function Test-CdpUp {
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:$cdpPort/json/version" -UseBasicParsing -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

if (Test-CdpUp) {
    Write-Host "[ok] CDP already on port $cdpPort"
    exit 0
}

# Stale lock from crashed Playwright (optional cleanup)
foreach ($f in @(
        (Join-Path $profile "SingletonLock"),
        (Join-Path $profile "SingletonCookie")
    )) {
    if (Test-Path -LiteralPath $f) {
        Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue
    }
}

New-Item -ItemType Directory -Force -Path $profile | Out-Null
Write-Host "Starting Google Chrome CDP port $cdpPort profile=$profile" -ForegroundColor Cyan
Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=$cdpPort",
    "--user-data-dir=$profile",
    $startUrl
)
Start-Sleep -Seconds 4

if (-not (Test-CdpUp)) {
    Write-Host "[fail] CDP not ready — close other Chrome using same profile, then re-run." -ForegroundColor Yellow
    exit 1
}
Write-Host "[ok] CDP ready — log in to NVIDIA if prompted, then run benefits script." -ForegroundColor Green
exit 0
