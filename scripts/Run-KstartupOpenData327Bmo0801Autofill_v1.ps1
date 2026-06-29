#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327 — K-Startup BMO0801 자동입력 (과제 20460558 기본).
.PARAMETER UseDefaultProfile
  모든 Chrome 창을 닫은 뒤, 일반 Chrome(기본 프로필) + CDP — 일반 Chrome에만 로그인된 경우.
.PARAMETER CdpPort
  remote-debugging-port (기본 9223).
#>
param(
    [switch]$UseDefaultProfile,
    [int]$CdpPort = 9223,
    [int]$WaitSec = 180,
    [string]$TaskId = "20460558"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$formUrl = "https://pms.k-startup.go.kr/biz/screen/BMO1101M0100"

$chromeCandidates = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chrome) { Write-Error "Google Chrome not found" }

function Test-CdpUp {
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:$CdpPort/json/version" -UseBasicParsing -TimeoutSec 2
        return $true
    } catch { return $false }
}

if (-not (Test-CdpUp)) {
    if ($UseDefaultProfile) {
        $userData = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"
        Write-Host "Default Chrome profile + CDP (close ALL Chrome windows first)." -ForegroundColor Yellow
        $chromeArgs = @(
            "--remote-debugging-port=$CdpPort",
            "--user-data-dir=`"$userData`"",
            "--profile-directory=Default",
            $formUrl
        )
    } else {
        $profile = Join-Path $env:LOCALAPPDATA "kstartup-cdp-profile"
        New-Item -ItemType Directory -Force -Path $profile | Out-Null
        Write-Host "Isolated CDP profile: $profile — log in in THIS window." -ForegroundColor Cyan
        $chromeArgs = @(
            "--remote-debugging-port=$CdpPort",
            "--user-data-dir=$profile",
            $formUrl
        )
    }
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs
    Start-Sleep -Seconds 3
}

if (-not (Test-CdpUp)) {
    Write-Host "CDP port $CdpPort not ready — log in manually, then re-run." -ForegroundColor Yellow
    exit 1
}

Write-Host "Playwright BMO0801 autofill (task $TaskId, wait login ${WaitSec}s)..." -ForegroundColor Cyan
py scripts/kstartup_opendata327_bmo0801_autofill_v1.py `
    --cdp-url "http://127.0.0.1:$CdpPort" `
    --task-id $TaskId `
    --wait-for-login-sec $WaitSec
exit $LASTEXITCODE
