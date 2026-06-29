<#
.SYNOPSIS
  Bootstrap logos.jema-ai.com on VPS: nginx (HTTP) + certbot + SSL vhost when cert exists.

.DESCRIPTION
  1) scp nginx configs to VPS repo path
  2) install bootstrap vhost (port 80 → :3010)
  3) certbot --nginx -d logos.jema-ai.com (best-effort; needs CF CNAME first)
  4) apply full SSL vhost when cert dir exists

  DNS (Tier 3 if API 403): Cloudflare jema-ai.com zone → CNAME `logos` → `app.jema-ai.com` (proxied).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LogosJemaAiInfraBootstrap_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SshHost = "",
    [switch]$SkipCertbot,
    [switch]$SkipDnsEnsure
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
. (Join-Path $PSScriptRoot "MkmVpsRemoteCommon_v1.ps1")

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

if (-not $SshHost) {
    $SshHost = Get-EnvAny "MKM_VPS_HOST"
    if (-not $SshHost) { $SshHost = "vps-mkmlife" }
}
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$vpsRepo = "/opt/mkm-destiny-ai-41e38ec6"
$deployLinux = Join-Path $WorkspaceRoot "scripts\deploy\linux"
$t = Get-MkmVpsRemoteTarget

$files = @(
    "nginx-logos-jema-ai-com.conf.example",
    "nginx-logos-jema-ai-com.bootstrap.conf",
    "apply_logos_jema_ai_nginx_v1.sh"
)
foreach ($f in $files) {
    $local = Join-Path $deployLinux $f
    if (-not (Test-Path $local)) { throw "missing $local" }
    Invoke-MkmVpsScp -LocalPath $local -RemoteSpec ("{0}:{1}/scripts/deploy/linux/" -f $t.Remote, $vpsRepo)
}

if (-not $SkipDnsEnsure) {
    Write-Host "[logos-infra] Cloudflare DNS ensure (API)" -ForegroundColor Cyan
    & py (Join-Path $WorkspaceRoot "scripts\setup_cloudflare_logos_jema_ai_dns_v1.py")
    $dnsCode = $LASTEXITCODE
    if ($dnsCode -ne 0) {
        Write-Host "[logos-infra] WARN: DNS API exit $dnsCode — add CF CNAME logos -> app.jema-ai.com manually (proxied)" -ForegroundColor Yellow
    }
}

$remoteCmd = (@"
set -e
chmod +x $vpsRepo/scripts/deploy/linux/apply_logos_jema_ai_nginx_v1.sh
cp -a $vpsRepo/scripts/deploy/linux/nginx-logos-jema-ai-com.bootstrap.conf /etc/nginx/sites-available/logos.jema-ai.com.bootstrap
ln -sf /etc/nginx/sites-available/logos.jema-ai.com.bootstrap /etc/nginx/sites-enabled/logos.jema-ai.com
nginx -t
systemctl reload nginx 2>/dev/null || nginx -s reload
echo '[logos-infra] bootstrap nginx OK'
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"

Write-Host "[logos-infra] install bootstrap nginx host=$($t.HostName)" -ForegroundColor Cyan
Invoke-MkmVpsSsh -RemoteCommand $remoteCmd

if (-not $SkipCertbot) {
    $certCmd = (@"
if command -v certbot >/dev/null 2>&1; then
  certbot certonly --webroot -w /var/www/certbot -d logos.jema-ai.com \
    --non-interactive --agree-tos -m support@mkmlife.com --keep-until-expiring 2>&1 || true
else
  echo '[logos-infra] certbot not installed — skip'
fi
if [ -d /etc/letsencrypt/live/logos.jema-ai.com ]; then
  bash $vpsRepo/scripts/deploy/linux/apply_logos_jema_ai_nginx_v1.sh -y
  echo '[logos-infra] SSL vhost applied'
else
  echo '[logos-infra] WARN: no cert yet — after CF DNS, rerun certbot then apply_logos_jema_ai_nginx_v1.sh -y'
fi
"@).Replace("`r`n", "`n").Replace("`r", "`n").TrimEnd() + "`n"
    Write-Host "[logos-infra] certbot (best-effort)" -ForegroundColor Cyan
    Invoke-MkmVpsSsh -RemoteCommand $certCmd
}

Write-Host "[logos-infra] public smoke" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\verify_logos_jema_ai_deploy_v1.ps1")
exit $LASTEXITCODE
