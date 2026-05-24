#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only VPS nginx SSL option audit (protocol redefined warnings).
  Writes reports/vps_nginx_ssl_protocol_audit_v1_latest.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-EnvAny([string]$name) {
    foreach ($scope in @("Process", "User", "Machine")) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    }
    return ""
}

$root = $WorkspaceRoot
if (-not $OutJson) {
    $OutJson = Join-Path $root "reports\vps_nginx_ssl_protocol_audit_v1_latest.json"
}

$hostFqdn = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"

if (-not $hostFqdn) {
    $payload = @{
        schema = "vps_nginx_ssl_protocol_audit_v1"
        ok = $false
        skipped = $true
        reason = "MKM_VPS_HOST unset"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $payload | ConvertTo-Json -Depth 6 | Set-Content -Path $OutJson -Encoding UTF8
    Write-Host "[ssl-audit] SKIP: MKM_VPS_HOST unset -> $OutJson"
    exit 2
}

$remote = "set -e; echo '=== nginx -t ==='; sudo nginx -t 2>&1 || true; " +
    "echo '=== ssl_protocol/ssl_ciphers in sites-enabled ==='; " +
    "sudo grep -RhnE 'ssl_protocols|ssl_ciphers|listen .*443' /etc/nginx/sites-enabled 2>/dev/null | head -n 120 || true; " +
    "echo '=== server_name (sites-enabled) ==='; " +
    "sudo grep -Rhn 'server_name' /etc/nginx/sites-enabled 2>/dev/null | head -n 80 || true"

$sshArgs = @()
if ($extra) {
    $sshArgs += ($extra -split '\s+')
}
# bash -c only (no login shell) — avoid dumping VPS env/secrets into audit JSON
$sshArgs += @("${user}@${hostFqdn}", "bash", "-c", $remote)

Write-Host "[ssl-audit] SSH ${user}@${hostFqdn} ..." -ForegroundColor Cyan
$lines = & ssh @sshArgs 2>&1
$raw = ($lines | Out-String).Trim()
$text = $raw
if ($text -match '(?s)(=== nginx -t ===.*)') { $text = $Matches[1].Trim() }
$text = [regex]::Replace($text, '(?m)^[A-Za-z_][A-Za-z0-9_]*=.*(\r?\n|$)', '')
$text = [regex]::Replace($text, '(?i)(api[_-]?key|secret|token|password)\s*=\s*\S+', '[REDACTED]')
$nginxOk = $raw -match "syntax is ok" -and $raw -match "test is successful"
$hasRedefined = $raw -match "protocol options redefined"
$vhosts = [regex]::Matches($raw, 'sites-enabled/([^:]+):') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Unique

$report = [ordered]@{
    schema = "vps_nginx_ssl_protocol_audit_v1"
    host = $hostFqdn
    user = $user
    nginx_test_ok = [bool]$nginxOk
    protocol_options_redefined_seen = [bool]$hasRedefined
    affected_vhosts = @($vhosts)
    ok = [bool]$nginxOk
    repair_hint = "Move ssl_protocols/ssl_ciphers to one snippet; remove per-vhost duplicates on same listen 443 socket."
    stdout_excerpt = if ($text.Length -gt 6000) { $text.Substring(0, 6000) + "`n...(truncated)" } else { $text }
    stdout_redacted = $true
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
}

$report | ConvertTo-Json -Depth 6 | Set-Content -Path $OutJson -Encoding UTF8
Write-Host "[ssl-audit] nginx_test_ok=$($report.nginx_test_ok) redefined=$($report.protocol_options_redefined_seen) -> $OutJson"
if (-not $nginxOk) { exit 1 }
exit 0
