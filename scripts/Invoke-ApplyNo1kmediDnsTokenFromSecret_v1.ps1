#Requires -Version 5.1
<#
.SYNOPSIS
  Apply no1kmedi-only DNS token from secret JSON — does NOT overwrite CLOUDFLARE_API_TOKEN.

.INPUT
  reports/cloudflare_dns_token_create_secret_LOCAL.json
  Field: MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN (or CLOUDFLARE_API_TOKEN if dedicated key absent)
#>
param(
    [string]$SecretJson = "",
    [switch]$SkipDnsEnsure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $root "reports\cloudflare_dns_token_create_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    throw "Missing $SecretJson — paste Zone DNS Edit token for no1kmedi.com (see .template.json)."
}
$doc = Get-Content -LiteralPath $SecretJson -Raw | ConvertFrom-Json
$tok = [string]$doc.MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN
if ([string]::IsNullOrWhiteSpace($tok)) { $tok = [string]$doc.CLOUDFLARE_API_TOKEN }
if ([string]::IsNullOrWhiteSpace($tok)) { throw "Set MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN in $SecretJson" }

$envPath = Join-Path $root ".env"
$lines = @()
if (Test-Path -LiteralPath $envPath) { $lines = Get-Content -LiteralPath $envPath }
$out = New-Object System.Collections.Generic.List[string]
$replaced = $false
$key = "MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN"
foreach ($line in $lines) {
    if ($line -match '^\s*MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN=') {
        $out.Add("${key}=$tok")
        $replaced = $true
    }
    else { $out.Add($line) }
}
if (-not $replaced) { $out.Add("${key}=$tok") }
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
Write-Host "Updated .env $key (CLOUDFLARE_API_TOKEN unchanged)" -ForegroundColor Green

[Environment]::SetEnvironmentVariable($key, $tok, "User")
[Environment]::SetEnvironmentVariable($key, $tok, "Process")

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDnsEnsure) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "Invoke-No1kmediCloudflareDnsEnsure_v1.ps1") -SkipBrowser
    exit $LASTEXITCODE
}
exit 0
