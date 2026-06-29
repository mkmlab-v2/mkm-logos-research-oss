#Requires -Version 5.1
<#
.SYNOPSIS
  창업패키지 340 — 일반 Chrome + paste assistant (CDP/NVIDIA 프로필과 별도).
  임시저장·제출은 human (공동인증서·G0 attest 후).
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

py scripts/build_kstartup_startup_package_ai_paste_ready_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/build_kstartup_startup_package_ai_paste_assistant_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$formUrl = "https://pms.k-startup.go.kr/biz/screen/BMO0101M01?pbancId=0661001"
$assistant = Join-Path $root "reports\demo\kstartup_startup_package_ai_paste_assistant_v1.html"
$order = Join-Path $root "reports\kstartup_startup_package_ai_paste_ready\00_paste_order.txt"
if (Test-Path -LiteralPath $order) {
    Set-Clipboard -Value (Get-Content -LiteralPath $order -Raw -Encoding UTF8)
}

Write-Host "Startup package 340 external paste pack" -ForegroundColor Cyan
Write-Host "  G0: reports/kstartup_startup_package_ai_g0_human_checklist_v1.txt (4항 NO 확인 후 attest)" -ForegroundColor Yellow
Write-Host "  Clipboard: 00_paste_order.txt" -ForegroundColor Yellow
Write-Host "  PMS:       $formUrl"
Write-Host "  Assistant: $assistant"
Write-Host "  Runbook:   reports/kstartup_startup_package_ai_submit_runbook_v1.txt"

Start-Process $formUrl
Start-Sleep -Milliseconds 400
Start-Process $assistant
exit 0
