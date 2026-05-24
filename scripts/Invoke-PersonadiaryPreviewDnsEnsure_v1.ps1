#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure preview.personadiary.com CNAME -> personadiary.com (Cloudflare proxied).
#>
param(
    [switch]$Apply,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ensure = Join-Path $root "scripts\Invoke-JemaaiCloudCloudflareDnsEnsure_v1.ps1"
$out = Join-Path $root "reports\cloudflare_dns_ensure_preview_personadiary_com.json"
$fixture = Join-Path $root "scripts\data\hostinger_full_exit\personadiary_cloudflare_zone_v1.json"
$trustedZoneId = ""
if (Test-Path -LiteralPath $fixture) {
    try {
        $fx = Get-Content -LiteralPath $fixture -Raw | ConvertFrom-Json
        if ($fx.zone_id) { $trustedZoneId = [string]$fx.zone_id }
    } catch { }
}

$argList = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $ensure,
    "-ZoneName", "personadiary.com",
    "-WwwLabel", "preview",
    "-CnameTarget", "personadiary.com",
    "-OutJson", $out
)
if ($trustedZoneId) {
    $argList += @("-TrustedZoneId", $trustedZoneId)
}
if ($WhatIf -or -not $Apply) {
    $argList += "-WhatIf"
}

& powershell.exe @argList
$code = $LASTEXITCODE
Write-Host "preview DNS ensure exit=$code out=$out"
exit $code
