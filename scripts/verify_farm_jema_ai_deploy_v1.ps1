<#
.SYNOPSIS
  Post-deploy smoke for https://farm.jema-ai.com (HTTP + HTML markers).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_farm_jema_ai_deploy_v1.ps1
#>
param(
    [string]$Url = "https://farm.jema-ai.com/",
    [string]$OutJson = "reports/farm_jema_ai_deploy_verify_latest.json"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$markers = @(
    "MKM Agriculture IoT",
    "smartfarm-page",
    "sf-system-flow",
    'id="flow"',
    'id="scale"',
    'id="roles"',
    "LoRa",
    "LTE/USIM",
    "support@mkmlife.com"
)

$code = & curl.exe -s -o NUL -w "%{http_code}" -L --max-time 30 $Url
$htmlPath = Join-Path $env:TEMP "farm-jema-ai-verify.html"
& curl.exe -s -L --max-time 30 -o $htmlPath $Url | Out-Null
$html = ""
if (Test-Path $htmlPath) {
    $html = [System.IO.File]::ReadAllText($htmlPath, [System.Text.UTF8Encoding]::new($false))
}

$found = @()
$missing = @()
foreach ($m in $markers) {
    if ($html -and $html.Contains($m)) { $found += $m } else { $missing += $m }
}

$ok = ($code -eq "200") -and ($missing.Count -eq 0)
$report = @{
    schema            = "farm_jema_ai_deploy_verify_v1"
    checked_at        = (Get-Date).ToUniversalTime().ToString("o")
    url               = $Url
    http_code         = [int]$code
    markers_ok        = ($missing.Count -eq 0)
    markers_found     = $found
    markers_missing   = $missing
    ok                = $ok
}

$outPath = Join-Path $root $OutJson
$dir = Split-Path $outPath -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$report | ConvertTo-Json -Depth 5 | Set-Content -Path $outPath -Encoding UTF8

if (-not $ok) {
    Write-Host "[farm-verify] FAIL http=$code missing=$($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[farm-verify] OK http=$code report=$outPath" -ForegroundColor Green
exit 0
