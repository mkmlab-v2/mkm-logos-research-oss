<#
.SYNOPSIS
  Apply MKM Family Google OAuth secrets from Windows DPAPI store to no1kmedi .env.local (no stdout secrets).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyMkmFamilyGoogleOAuthFromDpapi_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$EnvLocalPath = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $WorkspaceRoot).Path
$ps1 = Join-Path $root "scripts\Invoke-EncryptedSecretStore.ps1"
if (-not (Test-Path $ps1)) {
    Write-Error "Missing $ps1"
}

$target = if ($EnvLocalPath) { $EnvLocalPath } else { Join-Path $root "projects\no1kmedi\.env.local" }

function Get-DpapiPlain([string]$Key) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ps1 -Action get -Key $Key -AsPlainText 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $t = ($out | Out-String).Trim()
        if (-not $t) { return $null }
        return $t
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

$keys = @(
    "MKM_FAMILY_AUTH_SECRET",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET"
)

$lines = @()
if (Test-Path $target) {
    $lines = Get-Content -Path $target -Encoding UTF8
}

function Set-Or-Add([string]$name, [string]$value) {
    $script:lines = $script:lines | Where-Object { $_ -notmatch "^\s*$([regex]::Escape($name))\s*=" }
    $script:lines += "$name=$value"
}

$written = 0
foreach ($k in $keys) {
    $plain = Get-DpapiPlain $k
    if ($plain) {
        Set-Or-Add $k $plain
        $written++
    }
}

if ($written -eq 0) {
    Write-Host "[mkm-family-oauth] No DPAPI keys found; nothing written to $target"
    exit 1
}

$dir = Split-Path $target -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
Set-Content -Path $target -Value ($lines -join "`n") -Encoding UTF8 -NoNewline
Write-Host "[mkm-family-oauth] Updated $written key(s) in $target (values not printed)"
exit 0
