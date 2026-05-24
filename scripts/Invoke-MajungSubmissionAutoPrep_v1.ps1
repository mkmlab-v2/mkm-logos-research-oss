#Requires -Version 5.1
<#
.SYNOPSIS
  K-Startup 마중 제출 — gates + paste pack + HWPX + 외부 브라우저·assistant·클립보드 (제출 human).
.PARAMETER ClipboardStep
  First clipboard section: Step1 | Step2 (default Step1).
#>
param(
    [ValidateSet("Step1", "Step2")]
    [string]$ClipboardStep = "Step1",
    [switch]$SkipHwpx,
    [switch]$SkipGates
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $SkipGates) {
    Write-Host "== paste pack readiness ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MsRq019PastePackReadiness_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_jema12_studio_oracle_redirect_v1.ps1
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN: O-P5 verify failed (optional if CF already green)" -ForegroundColor Yellow }
}

Write-Host "== K-Startup majung paste pack ==" -ForegroundColor Cyan
py scripts/build_kstartup_majung_paste_ready_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_kstartup_majung_paste_assistant_html_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_ms_rq019_paste_bundle_v1.py
py scripts/build_ms_rq019_paste_assistant_html_v1.py

if (-not $SkipHwpx) {
    Write-Host "== HWPX slot fill ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-MsMicrosoftMaJungBusinessPlanHwpx_v1.ps1
    if ($LASTEXITCODE -ne 0) { Write-Host "WARN: HWPX fill failed — open existing filled file if present" -ForegroundColor Yellow }
}

$pasteDir = Join-Path $root "reports\kstartup_majung_paste_ready"
$clipMap = @{
    Step1 = Join-Path $pasteDir "bmo0902_step1_gwaje_nae_yong_paste.txt"
    Step2 = Join-Path $pasteDir "bmo0902_need_problem_paste.txt"
}
$clipFile = $clipMap[$ClipboardStep]
if (-not (Test-Path -LiteralPath $clipFile)) { Write-Error "clipboard source missing: $clipFile" }
Set-Clipboard -Value (Get-Content -LiteralPath $clipFile -Raw -Encoding UTF8)

$formUrl = "https://pms.k-startup.go.kr/biz/screen/BMO0902M0100"
$assistant = Join-Path $root "reports\demo\kstartup_majung_paste_assistant_v1.html"
$hwpx = Join-Path $root "reports\hwpx_poc\ms_microsoft_ma_jung_filled_v1.hwpx"
$gif = Join-Path $root "reports\ms_rq019_paste_ready\ms_rq019_oracle_v6_visual_path_10s.gif"

Write-Host ""
Write-Host "K-Startup auto prep DONE" -ForegroundColor Green
Write-Host "  Clipboard ($ClipboardStep): $clipFile" -ForegroundColor Yellow
Write-Host "  Form:      $formUrl"
Write-Host "  Assistant: $assistant"
Write-Host "  HWPX:      $hwpx"
Write-Host "  GIF:       $gif"
Write-Host ""
Write-Host "Human: 로그인 → Ctrl+V → assistant 순서 → 임시저장 → 최종 제출" -ForegroundColor Cyan

Start-Process $formUrl
Start-Sleep -Milliseconds 500
Start-Process $assistant
if (Test-Path -LiteralPath $hwpx) { Start-Process $hwpx }
if (Test-Path -LiteralPath $gif) {
    Start-Process explorer.exe -ArgumentList "/select,`"$gif`""
}

exit 0
