#Requires -Version 5.1
<#
.SYNOPSIS
  Apply jema-ai.com redirect token from local secret → User env + .env → triage → smartfarm CF rule.
  Sets MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN only (never overwrites CLOUDFLARE_API_TOKEN).
#>
param(
    [string]$SecretJson = "",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $WorkspaceRoot "reports\cloudflare_jema_ai_redirect_token_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    Write-Host "Missing $SecretJson" -ForegroundColor Yellow
    Write-Host "Dashboard: edit CLOUDFLARE_RULESETS_API_TOKEN → jema-ai.com Zone Read + Zone Rulesets" -ForegroundColor Cyan
    exit 2
}
$doc = Get-Content -LiteralPath $SecretJson -Raw -Encoding UTF8 | ConvertFrom-Json
$tok = [string]$doc.MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN
if ([string]::IsNullOrWhiteSpace($tok)) { $tok = [string]$doc.CLOUDFLARE_RULESETS_API_TOKEN }
if ([string]::IsNullOrWhiteSpace($tok)) { throw "Token empty in $SecretJson" }

$envPath = Join-Path $WorkspaceRoot ".env"
$lines = if (Test-Path -LiteralPath $envPath) { Get-Content -LiteralPath $envPath } else { @() }
$line = "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN=$tok"
$out = New-Object System.Collections.Generic.List[string]
$replaced = $false
foreach ($l in $lines) {
    if ($l -match '^\s*MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN=') {
        $out.Add($line)
        $replaced = $true
    } else { $out.Add($l) }
}
if (-not $replaced) { $out.Add($line) }
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
Write-Host "Updated .env MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN only" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN", $tok, "User")
[Environment]::SetEnvironmentVariable("MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN", $tok, "Process")
Write-Host "SET User+Process MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN" -ForegroundColor Green

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1")

py scripts/check_cloudflare_token_roles_v1.py 2>&1 | Out-Host
if ($LASTEXITCODE -gt 2) { exit $LASTEXITCODE }

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-CloudflareJemaAiSmartfarmRedirect_v1.ps1") -SkipTriage
exit $LASTEXITCODE
