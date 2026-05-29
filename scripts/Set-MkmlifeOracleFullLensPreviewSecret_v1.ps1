#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure MKM_ORACLE_FULL_LENSES_PREVIEW_TOKEN is set in mkm-life/.env.local and mkmlife Cloudflare Worker secret.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-MkmlifeOracleFullLensPreviewSecret_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-MkmlifeOracleFullLensPreviewSecret_v1.ps1 -WhatIfOnly
#>
param(
    [switch]$SkipCloudflare,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

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
    $lines = @()
    if (Test-Path -LiteralPath $path) {
        $lines = [System.Collections.Generic.List[string]]@(
            Get-Content -LiteralPath $path -Encoding UTF8
        )
    } else {
        $lines = [System.Collections.Generic.List[string]]@()
    }
    $pattern = "^\s*$([regex]::Escape($key))\s*="
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) { $idx = $i; break }
    }
    $newLine = "$key=$value"
    if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $path -Value ($lines -join "`n") -Encoding UTF8 -NoNewline
    Add-Content -LiteralPath $path -Value "`n" -Encoding UTF8
}

$keyName = "MKM_ORACLE_FULL_LENSES_PREVIEW_TOKEN"
$mkmLifeLocal = Join-Path $root "projects\mkm\mkm-life\.env.local"

$token = Get-EnvAny $keyName
if (-not $token) { $token = Read-DotEnvKey $mkmLifeLocal $keyName }
if (-not $token) {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    Write-Host "[oracle-preview-secret] generated new token (not printed)"
}

if ($WhatIfOnly) {
    Write-Host "[oracle-preview-secret] WhatIf: would upsert $keyName in mkm-life/.env.local"
    if (-not $SkipCloudflare) { Write-Host "[oracle-preview-secret] WhatIf: would wrangler secret put on mkmlife worker" }
    exit 0
}

Upsert-DotEnvKey $mkmLifeLocal $keyName $token
Write-Host "[oracle-preview-secret] mkm-life/.env.local updated"

if (-not $SkipCloudflare) {
    $mkmRoot = Join-Path $root "projects\mkm\mkm-life"
    Push-Location $mkmRoot
    try {
        $savedCf = $env:CLOUDFLARE_API_TOKEN
        $savedCfAlias = $env:CF_API_TOKEN
        if (-not $env:MKM_WRANGLER_FORCE_API_TOKEN) {
            Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
            Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
        }
        $token | npx wrangler secret put $keyName --config wrangler.jsonc
        if ($LASTEXITCODE -ne 0) { throw "wrangler secret put failed (exit $LASTEXITCODE)" }
        if ($null -ne $savedCf) { $env:CLOUDFLARE_API_TOKEN = $savedCf }
        if ($null -ne $savedCfAlias) { $env:CF_API_TOKEN = $savedCfAlias }
        Write-Host "[oracle-preview-secret] Cloudflare Worker secret updated"
    } finally {
        Pop-Location
    }
}

Write-Host "[oracle-preview-secret] done (token not logged)"
Write-Host "[oracle-preview-secret] preview URL pattern: https://mkmlife.com/oracle-sphere?lenses=full&preview=<token>"
