#Requires -Version 5.1
<#
.SYNOPSIS
  Sync SAJU_VERIFY_REMOTE_URL + SAJU_VERIFY_REMOTE_TOKEN to mkm-life .env.local and Cloudflare Worker secrets.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-MkmlifeSajuVerifyRemoteSecret_v1.ps1
#>
param(
    [switch]$SkipCloudflare,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Read-DotEnvKey([string]$path, [string]$key) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    foreach ($line in Get-Content -LiteralPath $path -Encoding UTF8) {
        if ($line -match "^\s*$([regex]::Escape($key))\s*=\s*(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function Upsert-DotEnvKey([string]$path, [string]$key, [string]$value) {
    $lines = [System.Collections.Generic.List[string]]@()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]](Get-Content -LiteralPath $path -Encoding UTF8)
    }
    $pattern = "^\s*$([regex]::Escape($key))\s*="
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) { $idx = $i; break }
    }
    $newLine = "$key=$value"
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
    Set-Content -LiteralPath $path -Value ($lines -join "`n") -Encoding UTF8
}

$envPath = Join-Path $root ".env"
$mkmEnvLocal = Join-Path $root "projects\mkm\mkm-life\.env.local"
$mkmDir = Join-Path $root "projects\mkm\mkm-life"

$remoteUrl = Read-DotEnvKey $envPath "SAJU_VERIFY_REMOTE_URL"
if (-not $remoteUrl) {
    $legacy = Read-DotEnvKey $envPath "ATHENA_MANSERYEOK_API_URL"
    if ($legacy -match "/reference$") {
        $remoteUrl = $legacy -replace "/reference$", "/verify-lite"
    } elseif ($legacy -match "saju-api\.no1kmedi\.com") {
        $remoteUrl = "https://app.jema-ai.com/api/manseryeok/verify-lite"
    } elseif ($legacy) {
        $remoteUrl = ($legacy.TrimEnd("/")) + "/verify-lite"
    }
}
if (-not $remoteUrl) {
    $remoteUrl = "https://app.jema-ai.com/api/manseryeok/verify-lite"
}

$remoteToken = Read-DotEnvKey $envPath "SAJU_VERIFY_REMOTE_TOKEN"
if (-not $remoteToken) {
    $remoteToken = Read-DotEnvKey $envPath "ATHENA_MANSERYEOK_API_TOKEN"
}

Write-Host "[saju-verify-remote] url=$remoteUrl token_set=$([bool]$remoteToken)" -ForegroundColor Cyan

if (-not $WhatIfOnly) {
    Upsert-DotEnvKey $mkmEnvLocal "SAJU_VERIFY_REMOTE_URL" $remoteUrl
    if ($remoteToken) {
        Upsert-DotEnvKey $mkmEnvLocal "SAJU_VERIFY_REMOTE_TOKEN" $remoteToken
    }
    Write-Host "[saju-verify-remote] updated $mkmEnvLocal" -ForegroundColor Green
}

if ($SkipCloudflare) {
    Write-Host "[saju-verify-remote] SkipCloudflare" -ForegroundColor Yellow
    exit 0
}

Push-Location $mkmDir
try {
    if ($WhatIfOnly) {
        Write-Host "[whatif] wrangler secret put SAJU_VERIFY_REMOTE_URL" -ForegroundColor DarkGray
        if ($remoteToken) { Write-Host "[whatif] wrangler secret put SAJU_VERIFY_REMOTE_TOKEN" -ForegroundColor DarkGray }
        exit 0
    }
    $remoteUrl | npx wrangler secret put SAJU_VERIFY_REMOTE_URL 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "wrangler SAJU_VERIFY_REMOTE_URL exit $LASTEXITCODE" }
    if ($remoteToken) {
        $remoteToken | npx wrangler secret put SAJU_VERIFY_REMOTE_TOKEN 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "wrangler SAJU_VERIFY_REMOTE_TOKEN exit $LASTEXITCODE" }
    }
    Write-Host "[saju-verify-remote] wrangler secrets updated" -ForegroundColor Green
} finally {
    Pop-Location
}
