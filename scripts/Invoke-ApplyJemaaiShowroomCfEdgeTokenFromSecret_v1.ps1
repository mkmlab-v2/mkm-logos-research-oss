#Requires -Version 5.1
<#
.SYNOPSIS
  Apply jemaai rulesets token from local secret JSON → .env + User sync → check → apply → autoverify.
  Does NOT overwrite MKM_MKMLIFE_CF_ANALYTICS_TOKEN (mkmlife UV stays separate).
#>
param(
    [string]$SecretJson = "",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $WorkspaceRoot "reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    Write-Host "Missing $SecretJson" -ForegroundColor Yellow
    Write-Host "Run: powershell -File scripts\Open-JemaaiShowroomCfEdgeTokenTemplate_v1.ps1" -ForegroundColor Cyan
    exit 2
}
$doc = Get-Content -LiteralPath $SecretJson -Raw -Encoding UTF8 | ConvertFrom-Json
$tok = [string]$doc.CLOUDFLARE_RULESETS_API_TOKEN
if ([string]::IsNullOrWhiteSpace($tok)) { $tok = [string]$doc.CLOUDFLARE_API_TOKEN }
if ([string]::IsNullOrWhiteSpace($tok)) { throw "Token empty in $SecretJson (use CLOUDFLARE_RULESETS_API_TOKEN)" }

$envPath = Join-Path $WorkspaceRoot ".env"
$lines = if (Test-Path -LiteralPath $envPath) { Get-Content -LiteralPath $envPath } else { @() }
$line = "CLOUDFLARE_RULESETS_API_TOKEN=$tok"
$out = New-Object System.Collections.Generic.List[string]
$replaced = $false
foreach ($l in $lines) {
    if ($l -match '^\s*CLOUDFLARE_RULESETS_API_TOKEN=') {
        $out.Add($line)
        $replaced = $true
    } else { $out.Add($l) }
}
if (-not $replaced) { $out.Add($line) }
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
Write-Host "Updated .env CLOUDFLARE_RULESETS_API_TOKEN only (CLOUDFLARE_API_TOKEN unchanged)" -ForegroundColor Green

[Environment]::SetEnvironmentVariable("CLOUDFLARE_RULESETS_API_TOKEN", $tok, "User")
[Environment]::SetEnvironmentVariable("CLOUDFLARE_RULESETS_API_TOKEN", $tok, "Process")
Write-Host "SET User+Process CLOUDFLARE_RULESETS_API_TOKEN" -ForegroundColor Green

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1")

Write-Host "==> check token" -ForegroundColor Cyan
py scripts/check_jemaai_cloud_cf_rules_token_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> apply edge rules" -ForegroundColor Cyan
py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1") -SkipApply -SkipVpsSync
exit $LASTEXITCODE
