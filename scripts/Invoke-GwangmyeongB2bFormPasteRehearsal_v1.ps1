# [HYPO] One-click: barrier audit + paste assistant local rehearsal (no Solapi, no submit).
param(
    [switch]$ServeAssistant,
    [int]$Port = 8765
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host '=== gwangmyeong B2B paste rehearsal ===' -ForegroundColor Cyan
py scripts/rehearse_gwangmyeong_baekje_b2b_form_paste_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$out = Join-Path $root 'reports/demo/gwangmyeong_baekje_b2b_form_paste_rehearsal_v1_latest.json'
Write-Host "artifact: $out" -ForegroundColor Green

if ($ServeAssistant) {
    $demo = Join-Path $root 'reports/demo'
    Write-Host "serving paste assistant on http://127.0.0.1:$Port/ (Ctrl+C to stop)" -ForegroundColor Yellow
    Set-Location $demo
    py -m http.server $Port
}
