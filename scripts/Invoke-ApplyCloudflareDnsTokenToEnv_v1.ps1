#Requires -Version 5.1
<#
.SYNOPSIS
  After manual CF token create: apply secret JSON to .env + User env sync + mkmlab DNS ensure.

.INPUT
  reports/cloudflare_dns_token_create_secret_LOCAL.json (from dashboard copy-paste helper)

.PARAMETER SecretJson
  Override path to JSON with CLOUDFLARE_API_TOKEN field.

.PARAMETER SkipDnsEnsure
  Only update .env and sync User env.
#>
param(
    [string]$SecretJson = "",
    [switch]$SkipDnsEnsure,
    [string]$OriginIp = "148.230.97.246"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $root "reports\cloudflare_dns_token_create_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    throw "Missing $SecretJson — paste token from CF dashboard into this file (schema cloudflare_dns_token_secret_v1)."
}
$doc = Get-Content -LiteralPath $SecretJson -Raw | ConvertFrom-Json
$tok = [string]$doc.CLOUDFLARE_API_TOKEN
if ([string]::IsNullOrWhiteSpace($tok)) { throw "CLOUDFLARE_API_TOKEN empty in $SecretJson" }

$envPath = Join-Path $root ".env"
$bak = Join-Path $root "reports\.env.bak_cloudflare_dns_token"
if (Test-Path -LiteralPath $envPath) {
    Copy-Item -LiteralPath $envPath -Destination $bak -Force
}
$lines = @()
if (Test-Path -LiteralPath $envPath) {
    $lines = Get-Content -LiteralPath $envPath
}
$out = New-Object System.Collections.Generic.List[string]
$replaced = $false
foreach ($line in $lines) {
    if ($line -match '^\s*CLOUDFLARE_API_TOKEN=') {
        $out.Add("CLOUDFLARE_API_TOKEN=$tok")
        $replaced = $true
    }
    else { $out.Add($line) }
}
if (-not $replaced) { $out.Add("CLOUDFLARE_API_TOKEN=$tok") }
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
Write-Host "Updated .env CLOUDFLARE_API_TOKEN (backup: $bak)" -ForegroundColor Green

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDnsEnsure) {
    $zid = "38a47f29983bd4ebce3798be08f59ba3"
    & py (Join-Path $root "scripts\ensure_mkmlab_space_cloudflare_dns_v1.py") --origin-ip $OriginIp --zone-id $zid
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
    exit $LASTEXITCODE
}
exit 0
