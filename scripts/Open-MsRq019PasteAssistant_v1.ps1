#Requires -Version 5.1
<#
.SYNOPSIS
  MS RQ-019 paste readiness gate + paste assistant HTML in default browser.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MsRq019PastePackReadiness_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$assistant = Join-Path $root "reports\demo\ms_rq019_paste_assistant_v1.html"
if (-not (Test-Path -LiteralPath $assistant)) {
    py scripts/build_ms_rq019_paste_assistant_html_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Opening paste assistant: $assistant" -ForegroundColor Cyan
Start-Process $assistant
exit 0
