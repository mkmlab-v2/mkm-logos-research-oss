#Requires -Version 5.1
<#
.SYNOPSIS
  Sync MKM_CONSUMER_PROFILE_BASIC_AUTH_* into mkm-life/.env.local and mkmlife Cloudflare Worker secrets.

.DESCRIPTION
  Consumer profile API uses httpOnly session bind by default. Optional Basic auth adds a second layer
  for /api/v1/consumer/* (middleware). Local dev with Basic auth enabled: set MKM_CONSUMER_PROFILE_DEV_OPEN=1
  in projects/mkm/mkm-life/.env.local (see .env.local.example).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-MkmlifeConsumerProfileGateSecret_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Set-MkmlifeConsumerProfileGateSecret_v1.ps1 -SkipCloudflare -WhatIfOnly
#>
param(
    [switch]$SkipCloudflare,
    [switch]$WhatIfOnly,
    [switch]$GeneratePassword
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

function Put-WranglerSecret([string]$mkmRoot, [string]$keyName, [string]$value) {
    $savedCf = $env:CLOUDFLARE_API_TOKEN
    $savedCfAlias = $env:CF_API_TOKEN
    if (-not $env:MKM_WRANGLER_FORCE_API_TOKEN) {
        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
        Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
    }
    $value | npx wrangler secret put $keyName --config wrangler.jsonc
    if ($LASTEXITCODE -ne 0) { throw "wrangler secret put $keyName failed (exit $LASTEXITCODE)" }
    if ($null -ne $savedCf) { $env:CLOUDFLARE_API_TOKEN = $savedCf }
    if ($null -ne $savedCfAlias) { $env:CF_API_TOKEN = $savedCfAlias }
}

$userKey = "MKM_CONSUMER_PROFILE_BASIC_AUTH_USER"
$passKey = "MKM_CONSUMER_PROFILE_BASIC_AUTH_PASS"
$workspaceEnv = Join-Path $root ".env"
$mkmLifeLocal = Join-Path $root "projects\mkm\mkm-life\.env.local"
$mkmRoot = Join-Path $root "projects\mkm\mkm-life"

$user = Get-EnvAny $userKey
if (-not $user) { $user = Read-DotEnvKey $workspaceEnv $userKey }
if (-not $user) { $user = Read-DotEnvKey $mkmLifeLocal $userKey }

$pass = Get-EnvAny $passKey
if (-not $pass) { $pass = Read-DotEnvKey $workspaceEnv $passKey }
if (-not $pass) { $pass = Read-DotEnvKey $mkmLifeLocal $passKey }

if (-not $user) {
    $user = "mkmlife-consumer-gate"
}

if (-not $pass) {
    if ($GeneratePassword) {
        $bytes = New-Object byte[] 24
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
        $pass = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        Write-Host "[consumer-profile-gate] generated new password (not printed)"
    } else {
        throw "Missing $passKey. Set in workspace .env or pass -GeneratePassword."
    }
}

if ($WhatIfOnly) {
    Write-Host "[consumer-profile-gate] WhatIf: would upsert $userKey and $passKey in mkm-life/.env.local"
    if (-not $SkipCloudflare) {
        Write-Host "[consumer-profile-gate] WhatIf: would wrangler secret put both keys on mkmlife worker"
    }
    exit 0
}

Upsert-DotEnvKey $mkmLifeLocal $userKey $user
Upsert-DotEnvKey $mkmLifeLocal $passKey $pass
Write-Host "[consumer-profile-gate] mkm-life/.env.local updated (values not logged)"

if (-not $SkipCloudflare) {
    Push-Location $mkmRoot
    try {
        Put-WranglerSecret $mkmRoot $userKey $user
        Put-WranglerSecret $mkmRoot $passKey $pass
        Write-Host "[consumer-profile-gate] Cloudflare Worker secrets updated"
    } finally {
        Pop-Location
    }
}

Write-Host "[consumer-profile-gate] done"
Write-Host "[consumer-profile-gate] local dev tip: MKM_CONSUMER_PROFILE_DEV_OPEN=1 skips bind/basic auth on localhost"
