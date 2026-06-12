<#
.SYNOPSIS
  Bootstrap MKM Family OAuth secrets in Windows DPAPI store.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Initialize-MkmFamilyGoogleOAuthSecureStore_v1.ps1 -GenerateAuthSecretOnly
.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Initialize-MkmFamilyGoogleOAuthSecureStore_v1.ps1
#>
param(
    [switch]$GenerateAuthSecretOnly,
    [switch]$ForceAuthSecret
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$storeScript = Join-Path $PSScriptRoot "Invoke-EncryptedSecretStore.ps1"
if (-not (Test-Path -LiteralPath $storeScript)) {
    throw "Missing $storeScript"
}

function Test-DpapiKey([string]$Key) {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action get -Key $Key -AsPlainText 2>$null
        if ($LASTEXITCODE -ne 0) { return $false }
        return -not [string]::IsNullOrWhiteSpace(($out | Out-String).Trim())
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

function Set-DpapiKey([string]$Key, [string]$Value) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $storeScript -Action set -Key $Key -Value $Value | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "DPAPI set failed for $Key" }
}

function New-AuthSecret {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

Write-Host "=== MKM Family Google OAuth — DPAPI bootstrap ===" -ForegroundColor Cyan

if (-not (Test-DpapiKey "MKM_FAMILY_AUTH_SECRET") -or $ForceAuthSecret) {
    $secret = New-AuthSecret
    Set-DpapiKey "MKM_FAMILY_AUTH_SECRET" $secret
    Write-Host "[ok] MKM_FAMILY_AUTH_SECRET generated and stored (value not printed)" -ForegroundColor Green
}
else {
    Write-Host "[skip] MKM_FAMILY_AUTH_SECRET already in store" -ForegroundColor DarkYellow
}

if ($GenerateAuthSecretOnly) {
    Write-Host "Done (-GenerateAuthSecretOnly). Add GOOGLE_OAUTH_* in Google Cloud Console, then re-run without switch." -ForegroundColor DarkCyan
    exit 0
}

function Prompt-Secret([string]$Key, [string]$Label, [switch]$Hidden) {
    if (Test-DpapiKey $Key) {
        Write-Host "[skip] $Key already in store" -ForegroundColor DarkYellow
        return
    }
    if ($Hidden) {
        $secure = Read-Host -Prompt $Label -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try { $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    else {
        $value = Read-Host -Prompt $Label
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "[skip] $Key empty" -ForegroundColor Yellow
        return
    }
    Set-DpapiKey $Key $value
    Write-Host "[ok] $Key stored" -ForegroundColor Green
}

Prompt-Secret "GOOGLE_OAUTH_CLIENT_ID" "Google OAuth Client ID"
Prompt-Secret "GOOGLE_OAUTH_CLIENT_SECRET" "Google OAuth Client Secret" -Hidden

Write-Host ""
Write-Host "Next: scripts\Invoke-ApplyMkmFamilyGoogleOAuthFromDpapi_v1.ps1" -ForegroundColor Cyan
Write-Host "VPS:   scripts\Invoke-ApplyMkmFamilyGoogleOAuthToVps_v1.ps1" -ForegroundColor Cyan
Write-Host "Redirect URI: https://app.jema-ai.com/api/mkm-family/auth/google/callback" -ForegroundColor DarkCyan
