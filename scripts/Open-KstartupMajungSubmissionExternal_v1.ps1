#Requires -Version 5.1
<#
.SYNOPSIS
  K-Startup 마중 양식 — Cursor 내장 브라우저 SSO(tokenInfoRelay) 우회용 외부 브라우저 런처.
  passni token relay / 간편인증 / 팝업 체인은 기본 Chrome·Edge에서만 진행.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$formUrl = "https://pms.k-startup.go.kr/biz/screen/BMO0902M0100"
$portalLogin = "https://www.k-startup.go.kr/web/contents/webLGIN.do?anyidLginUseYn=N"

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MsRq019PastePackReadiness_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$assistant = Join-Path $root "reports\demo\kstartup_majung_paste_assistant_v1.html"
if (-not (Test-Path -LiteralPath $assistant)) {
    py scripts/build_kstartup_majung_paste_assistant_html_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    py scripts/build_kstartup_majung_paste_assistant_html_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$step2 = Join-Path $root "reports\kstartup_majung_paste_ready\bmo0902_need_problem_paste.txt"
Set-Clipboard -Value (Get-Content -LiteralPath $step2 -Raw -Encoding UTF8)

Write-Host "K-Startup external browser launcher" -ForegroundColor Cyan
Write-Host "  Clipboard: Step2+ 문제·필요성 (Step1 이미 했다면 다음 칸에 붙여넣기)" -ForegroundColor Yellow
Write-Host "  Form:    $formUrl"
Write-Host "  Assistant: $assistant"

Start-Process $formUrl
Start-Sleep -Milliseconds 400
Start-Process $assistant

exit 0
