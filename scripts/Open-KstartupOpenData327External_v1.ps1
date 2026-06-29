#Requires -Version 5.1
<#
.SYNOPSIS
  로그인된 일반 Chrome + 붙여넣기 assistant (CDP 프로필과 별도).
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

py scripts/build_kstartup_opendata327_paste_assistant_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$formUrl = "https://pms.k-startup.go.kr/biz/screen/BMO0902M0100"
$assistant = Join-Path $root "reports\demo\kstartup_opendata327_paste_assistant_v1.html"
$clip = Join-Path $root "reports\kstartup_opendata327_paste_ready\step4_tsksNm.txt"
Set-Clipboard -Value (Get-Content -LiteralPath $clip -Raw -Encoding UTF8)

$chrome = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) { $chrome = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe" }

Write-Host "OpenData327 external paste pack" -ForegroundColor Cyan
Write-Host "  Clipboard: step4 task name" -ForegroundColor Yellow
Write-Host "  Form:      $formUrl"
Write-Host "  Assistant: $assistant"

Start-Process $formUrl
Start-Sleep -Milliseconds 400
Start-Process $assistant
exit 0
