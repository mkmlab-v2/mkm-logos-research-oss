#Requires -Version 5.1
<#
.SYNOPSIS
  Checks jema12.com public routes (root, broadcast, studio). Exit 0 if expectations met after handoff §7.
  Usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_jema12_public_routes.ps1
    $env:BASE_URL='https://www.jema12.com'; .\scripts\check_jema12_public_routes.ps1
#>
$ErrorActionPreference = "Stop"
$base = if ($env:BASE_URL) { $env:BASE_URL.TrimEnd('/') } else { "https://jema12.com" }

function Get-StatusLine {
    param([string]$Url)
    try {
        $r = Invoke-WebRequest -Uri $Url -Method Head -MaximumRedirection 0 -SkipHttpErrorCheck -TimeoutSec 25
        return [int]$r.StatusCode
    } catch {
        # Some stacks return response on redirect exception
        if ($_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode.value__
        }
        return -1
    }
}

function Get-StatusCurl {
    param([string]$Url)
    $u = [Uri]$Url
    & curl.exe -sSI -o NUL -w "%{http_code}" --max-time 25 $Url 2>$null
    if ($LASTEXITCODE -ne 0) { return "ERR" }
}

$failed = $false
Write-Host "== jema12 public route check ==" -ForegroundColor Cyan
Write-Host "BASE_URL=$base"

# Root: 200
$codeRoot = Get-StatusCurl "$base/"
if ($codeRoot -eq "200") { Write-Host "[PASS] GET / -> $codeRoot" -ForegroundColor Green }
else { Write-Host "[FAIL] GET / expected 200, got $codeRoot" -ForegroundColor Red; $failed = $true }

# After §7: /broadcast should be 302 (or 301) to showroom
$codeBc = Get-StatusCurl "$base/broadcast"
if ($codeBc -in @("302", "301", "200")) {
    Write-Host "[PASS] GET /broadcast -> $codeBc (accept 30x or 200)" -ForegroundColor Green
} else {
    Write-Host "[WARN] GET /broadcast -> $codeBc (expect 302 after nginx handoff; 404 until applied)" -ForegroundColor Yellow
    if ($codeBc -eq "404") { $failed = $true }
}

# /studio -> should not stay 404 if 301 to /studio/ is deployed
$codeSt = Get-StatusCurl "$base/studio"
if ($codeSt -in @("301", "302", "200")) {
    Write-Host "[PASS] GET /studio -> $codeSt" -ForegroundColor Green
} else {
    Write-Host "[WARN] GET /studio -> $codeSt (expect 301 to /studio/)" -ForegroundColor Yellow
}

# /studio/ should not be 500
$codeStSl = Get-StatusCurl "$base/studio/"
if ($codeStSl -eq "500") {
    Write-Host "[FAIL] GET /studio/ -> 500 (fix nginx root/alias or static path on server)" -ForegroundColor Red
    $failed = $true
} elseif ($codeStSl -in @("200", "301", "302", "304", "403")) {
    Write-Host "[PASS] GET /studio/ -> $codeStSl" -ForegroundColor Green
} else {
    Write-Host "[WARN] GET /studio/ -> $codeStSl" -ForegroundColor Yellow
}

if ($failed) {
    Write-Host "`nEXIT 1 — apply server: scripts/deploy/linux/apply_jema12_nginx_snippet.sh + docs/final/JEMA12_PUBLIC_DOMAIN_AND_DEPLOY_HANDOFF_2026-04-07.md §7" -ForegroundColor Red
    exit 1
}
Write-Host "`nEXIT 0" -ForegroundColor Green
exit 0
