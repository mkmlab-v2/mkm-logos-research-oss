#Requires -Version 5.1
# Apply token from secret → disable CF managed robots → verify Disallow /legacy/
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SecretJson = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($SecretJson)) {
    $SecretJson = Join-Path $WorkspaceRoot "reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json"
}
if (-not (Test-Path -LiteralPath $SecretJson)) {
    Write-Host "Missing $SecretJson — run Open-JemaaiRobotsBotManagementToken_v1.ps1 first" -ForegroundColor Yellow
    exit 2
}
$doc = Get-Content -LiteralPath $SecretJson -Raw -Encoding UTF8 | ConvertFrom-Json
$tok = [string]$doc.CLOUDFLARE_RULESETS_API_TOKEN
if ([string]::IsNullOrWhiteSpace($tok)) { $tok = [string]$doc.CLOUDFLARE_API_TOKEN }
if ([string]::IsNullOrWhiteSpace($tok)) { throw "Token empty in $SecretJson" }

$envPath = Join-Path $WorkspaceRoot ".env"
$lines = if (Test-Path -LiteralPath $envPath) { Get-Content -LiteralPath $envPath } else { @() }
$line = "CLOUDFLARE_RULESETS_API_TOKEN=$tok"
$out = New-Object System.Collections.Generic.List[string]
$replaced = $false
foreach ($l in $lines) {
    if ($l -match '^\s*CLOUDFLARE_RULESETS_API_TOKEN=') { $out.Add($line); $replaced = $true }
    else { $out.Add($l) }
}
if (-not $replaced) { $out.Add($line) }
$out | Set-Content -LiteralPath $envPath -Encoding UTF8
[Environment]::SetEnvironmentVariable("CLOUDFLARE_RULESETS_API_TOKEN", $tok, "User")
[Environment]::SetEnvironmentVariable("CLOUDFLARE_RULESETS_API_TOKEN", $tok, "Process")
Write-Host "Updated CLOUDFLARE_RULESETS_API_TOKEN" -ForegroundColor Green

py scripts/setup_cloudflare_jemaai_robots_legacy_v1.py
exit $LASTEXITCODE
