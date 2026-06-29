#Requires -Version 5.1

<#

.SYNOPSIS

  OpenData 327 — K-Startup BMO0902 첨부·온라인 자동입력 (과제 20460495).

.PARAMETER UseDefaultProfile

  모든 Chrome 창을 닫은 뒤, 일반 Chrome(기본 프로필) + CDP로 실행 — 일반 Chrome에만 로그인된 경우.

#>

param(

    [switch]$UseDefaultProfile,

    [int]$WaitSec = 300

)



$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Set-Location $root



$cdpPort = 9222

$formUrl = "https://pms.k-startup.go.kr/biz/screen/BMO0902M0100"



$chromeCandidates = @(

    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",

    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"

)

$chrome = $chromeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if (-not $chrome) { Write-Error "Google Chrome not found" }



function Test-CdpUp {

    try {

        $null = Invoke-WebRequest -Uri "http://127.0.0.1:$cdpPort/json/version" -UseBasicParsing -TimeoutSec 2

        return $true

    } catch { return $false }

}



if (-not (Test-CdpUp)) {

    if ($UseDefaultProfile) {

        $userData = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"

        Write-Host "Default Chrome profile + CDP (close ALL Chrome windows first)." -ForegroundColor Yellow

        Write-Host "  User Data: $userData" -ForegroundColor DarkGray

        $chromeArgs = @(

            "--remote-debugging-port=$cdpPort",

            "--user-data-dir=`"$userData`"",

            "--profile-directory=Default",

            $formUrl

        )

    } else {

        $profile = Join-Path $env:LOCALAPPDATA "kstartup-cdp-profile"

        New-Item -ItemType Directory -Force -Path $profile | Out-Null

        Write-Host "Isolated CDP profile: $profile — log in here if not using -UseDefaultProfile" -ForegroundColor Cyan

        $chromeArgs = @(

            "--remote-debugging-port=$cdpPort",

            "--user-data-dir=$profile",

            $formUrl

        )

    }

    Start-Process -FilePath $chrome -ArgumentList $chromeArgs

    Start-Sleep -Seconds 4

}



if (-not (Test-CdpUp)) {

    Write-Host "CDP not ready on port $cdpPort" -ForegroundColor Red

    exit 1

}



Write-Host "BMO0902 autofill (wait login ${WaitSec}s max)..." -ForegroundColor Cyan

py scripts/kstartup_opendata327_bmo0902_autofill_v1.py --cdp-url "http://127.0.0.1:$cdpPort" --wait-for-login-sec $WaitSec

exit $LASTEXITCODE

