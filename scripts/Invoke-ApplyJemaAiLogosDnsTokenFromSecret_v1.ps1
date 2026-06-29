#Requires -Version 5.1
<#
.SYNOPSIS
  Apply jema-ai.com DNS token from secret → User env + .env → logos CNAME ensure.

  Sets MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN only (never overwrites CLOUDFLARE_API_TOKEN).
#>
param(
    [string]$SecretJson = "",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $WorkspaceRoot "reports\cloudflare_jema_ai_logos_dns_token_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    Write-Host "Missing $SecretJson" -ForegroundColor Yellow
    exit 2
}
$doc = Get-Content -LiteralPath $SecretJson -Raw -Encoding UTF8 | ConvertFrom-Json
$tok = [string]$doc.MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN
if ([string]::IsNullOrWhiteSpace($tok)) { throw "MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN empty in $SecretJson" }

$envPath = Join-Path $WorkspaceRoot ".env"
$lines = if (Test-Path -LiteralPath $envPath) { Get-Content -LiteralPath $envPath } else { @() }
$line = "MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN=$tok"
$out = New-Object System.Collections.Generic.List[string]
$replaced = $false
foreach ($l in $lines) {
    if ($l -match '^\s*MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN=') {
        $out.Add($line)
        $replaced = $true
    } else { $out.Add($l) }
}
if (-not $replaced) { $out.Add($line) }
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
Write-Host "Updated .env MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN", $tok, "User")
[Environment]::SetEnvironmentVariable("MKM_CLOUDFLARE_JEMA_AI_DNS_TOKEN", $tok, "Process")

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py (Join-Path $WorkspaceRoot "scripts\setup_cloudflare_logos_jema_ai_dns_v1.py")
exit $LASTEXITCODE
