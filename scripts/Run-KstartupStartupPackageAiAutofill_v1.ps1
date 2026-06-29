#Requires -Version 5.1
<#
.SYNOPSIS
  2026 창업패키지(AI 인재 실증형) — K-Startup PMS CDP autofill (임시저장만).

.PARAMETER UseDefaultProfile
  Chrome 전부 닫은 뒤 일반 프로필 + CDP (이미 로그인된 경우).

.PARAMETER PmsUrl
  사업신청 화면 URL (주소창 복사). history 행 매칭 실패 시 사용.

.PARAMETER ProbeOnly
  필드 구조만 덤프 (reports/kstartup_startup_package_ai_pms_probe_latest.json).

.EXAMPLE
  powershell -File scripts\Run-KstartupStartupPackageAiAutofill_v1.ps1 -UseDefaultProfile

.EXAMPLE
  powershell -File scripts\Run-KstartupStartupPackageAiAutofill_v1.ps1 -PmsUrl "https://pms.k-startup.go.kr/..." -ProbeOnly
#>
param(
    [switch]$UseDefaultProfile,
    [string]$PmsUrl = "",
    [string]$PortalUrl = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?pbancClssCd=PBC010&schM=view&pbancSn=177670",
    [switch]$FromPortal,
    [switch]$ProbeOnly,
    [switch]$SkipSubmissionGate,
    [int]$WaitSec = 300
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$cdpPort = 9222
$historyUrl = "https://pms.k-startup.go.kr/biz/screen/NCOB0101M0100"

# 첨부 ingest + paste → filled docx/PDF (빈 양식 업로드 방지)
py (Join-Path $PSScriptRoot "ingest_kstartup_startup_package_ai_downloads_v1.py") 2>$null | Out-Null
py (Join-Path $PSScriptRoot "build_kstartup_startup_package_ai_paste_ready_v1.py") 2>$null | Out-Null
py (Join-Path $PSScriptRoot "fill_kstartup_startup_package_ai_doyak_docx_v1.py")
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: fill docx exit $LASTEXITCODE" -ForegroundColor Yellow }
py (Join-Path $PSScriptRoot "verify_kstartup_startup_package_ai_filled_plan_v1.py")
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: filled plan verify failed — autofill may skip upload" -ForegroundColor Yellow }

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
    $startUrl = if ($PmsUrl) { $PmsUrl } elseif ($FromPortal -or $PortalUrl) { $PortalUrl } else { $historyUrl }
    if ($UseDefaultProfile) {
        $userData = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"
        Write-Host "Default Chrome + CDP — close ALL Chrome windows first." -ForegroundColor Yellow
        $chromeArgs = @(
            "--remote-debugging-port=$cdpPort",
            "--user-data-dir=`"$userData`"",
            "--profile-directory=Default",
            $startUrl
        )
    } else {
        $profile = Join-Path $env:LOCALAPPDATA "kstartup-startuppkg-cdp-profile"
        New-Item -ItemType Directory -Force -Path $profile | Out-Null
        Write-Host "Isolated CDP profile: $profile — log in here." -ForegroundColor Cyan
        $chromeArgs = @(
            "--remote-debugging-port=$cdpPort",
            "--user-data-dir=$profile",
            $startUrl
        )
    }
    Start-Process -FilePath $chrome -ArgumentList $chromeArgs
    Start-Sleep -Seconds 4
}

if (-not (Test-CdpUp)) {
    Write-Host "CDP not ready on port $cdpPort" -ForegroundColor Red
    exit 1
}

$pyArgs = @(
    "scripts/kstartup_startup_package_ai_autofill_v1.py",
    "--cdp-url", "http://127.0.0.1:$cdpPort",
    "--wait-for-login-sec", "$WaitSec"
)
if ($PmsUrl) { $pyArgs += @("--pms-url", $PmsUrl) }
if ($FromPortal -or (-not $PmsUrl -and $PortalUrl)) {
    $pyArgs += @("--from-portal", "--portal-url", $PortalUrl)
}
if ($ProbeOnly) { $pyArgs += "--probe-only" }
if ($SkipSubmissionGate) { $pyArgs += "--skip-submission-gate" }

Write-Host "Startup package AI autofill (임시저장 only)..." -ForegroundColor Cyan
py @pyArgs
exit $LASTEXITCODE
