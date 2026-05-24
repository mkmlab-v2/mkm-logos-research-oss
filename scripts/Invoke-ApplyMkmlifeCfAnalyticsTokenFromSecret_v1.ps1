#Requires -Version 5.1
<#
.SYNOPSIS
  Apply mkmlife CF analytics token from local secret JSON → .env + User sync + probe.
#>
param(
    [string]$SecretJson = "",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $WorkspaceRoot "reports\cloudflare_mkmlife_analytics_token_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    throw "Missing $SecretJson — paste token from CF dashboard after create."
}
$doc = Get-Content -LiteralPath $SecretJson -Raw -Encoding UTF8 | ConvertFrom-Json
$tok = [string]($doc.MKM_MKMLIFE_CF_ANALYTICS_TOKEN)
if ([string]::IsNullOrWhiteSpace($tok)) { $tok = [string]$doc.CLOUDFLARE_API_TOKEN }
if ([string]::IsNullOrWhiteSpace($tok)) { throw "Token empty in $SecretJson" }

$envPath = Join-Path $WorkspaceRoot ".env"
$lines = if (Test-Path -LiteralPath $envPath) { Get-Content -LiteralPath $envPath } else { @() }
$keys = @("MKM_MKMLIFE_CF_ANALYTICS_TOKEN", "CLOUDFLARE_API_TOKEN")
$out = New-Object System.Collections.Generic.List[string]
$done = @{}
foreach ($line in $lines) {
    if ($line -match '^\s*(MKM_MKMLIFE_CF_ANALYTICS_TOKEN|CLOUDFLARE_API_TOKEN)=') {
        $k = ($line -split '=', 2)[0].Trim()
        if ($keys -contains $k -and -not $done[$k]) {
            $out.Add("$k=$tok")
            $done[$k] = $true
        }
    }
    else { $out.Add($line) }
}
foreach ($k in $keys) {
    if (-not $done[$k]) { $out.Add("$k=$tok") }
}
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
Write-Host "Updated .env (MKM_MKMLIFE_CF_ANALYTICS_TOKEN + CLOUDFLARE_API_TOKEN)" -ForegroundColor Green

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1")
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-MkmlifeCfAnalyticsEnvSetup_v1.ps1") -SkipTaskRegister -SkipSync
