# Recommended SSL fix: VPS clinic SAN + apex portal; CF guidance for www.clinic (DNS-only).
param([string]$WorkspaceRoot = "C:\workspace")
$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
Set-Location $root

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$sshArgs = @()
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

$vpsRepo = "/opt/mkm-destiny-ai-41e38ec6"
$fixSh = "fix_no1kmedi_domain_recommended_v1.sh"
$remoteFix = "$vpsRepo/scripts/deploy/linux/$fixSh"
$fixBody = @'
#!/usr/bin/env bash
set -euo pipefail
REPO="${MKM_REPO_ROOT:-/opt/mkm-destiny-ai-41e38ec6}"
log() { echo "[no1kmedi-recommended-fix] $*"; }
CLINIC_CERT="/etc/letsencrypt/live/clinic.no1kmedi.com/fullchain.pem"
if [[ -f "$CLINIC_CERT" ]]; then
  if ! openssl x509 -in "$CLINIC_CERT" -noout -text 2>/dev/null | grep -q 'www\.clinic\.no1kmedi\.com'; then
    certbot certonly --nginx -d clinic.no1kmedi.com -d www.clinic.no1kmedi.com --non-interactive --agree-tos -m admin@no1kmedi.com --expand || true
  fi
  bash "$REPO/scripts/deploy/linux/apply_clinic_no1kmedi_nginx_v1.sh" -y
fi
shopt -s nullglob
for legacy in /etc/nginx/sites-enabled/no1kmedi.com* /etc/nginx/sites-enabled/www.no1kmedi.com*; do
  base=$(basename "$legacy")
  [[ "$base" == "no1kmedi.com-portal" ]] && continue
  [[ "$base" == *.legacy-disabled ]] && continue
  mv "$legacy" "${legacy}.legacy-disabled" 2>/dev/null || rm -f "$legacy"
  log "Disabled legacy $legacy"
done
shopt -u nullglob
PORTAL_SSL_DIR="/etc/letsencrypt/live/no1kmedi.com"
if [[ ! -f "${PORTAL_SSL_DIR}/fullchain.pem" ]] && [[ -f /etc/letsencrypt/live/www.no1kmedi.com/fullchain.pem ]]; then
  PORTAL_SSL_DIR="/etc/letsencrypt/live/www.no1kmedi.com"
fi
if [[ -f "${PORTAL_SSL_DIR}/fullchain.pem" ]]; then
  export PORTAL_SSL_DIR
  bash "$REPO/scripts/deploy/linux/apply_no1kmedi_com_portal_nginx_v1.sh" -y
fi
nginx -t && (systemctl reload nginx 2>/dev/null || nginx -s reload)
log Done
'@
$localFix = Join-Path $env:TEMP "fix_no1kmedi_domain_recommended_v1.sh"
[System.IO.File]::WriteAllText($localFix, ($fixBody -replace "`r`n", "`n"), [System.Text.UTF8Encoding]::new($false))

& ssh @($sshArgs + @($remote, "mkdir -p $vpsRepo/scripts/deploy/linux"))
& scp @($sshArgs + @($localFix, "${remote}:${remoteFix}"))
& ssh @($sshArgs + @($remote, "sed -i 's/\r$//' $remoteFix; chmod +x $remoteFix; MKM_REPO_ROOT=$vpsRepo bash $remoteFix"))
$vpsEc = $LASTEXITCODE

$probes = [System.Collections.Generic.List[object]]::new()
$urls = @(
    "https://clinic.no1kmedi.com/",
    "https://www.clinic.no1kmedi.com/",
    "https://no1kmedi.com/",
    "https://research.no1kmedi.com/",
    "https://mkmlab.space/"
)
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $u -MaximumRedirection 5 -TimeoutSec 25 -UseBasicParsing
        $probes.Add([ordered]@{ url = $u; ok = $true; status = $r.StatusCode }) | Out-Null
    } catch {
        $probes.Add([ordered]@{ url = $u; ok = $false; error = $_.Exception.Message }) | Out-Null
    }
}

$out = @{
    schema           = "no1kmedi_domain_recommended_ssl_fix_v1"
    at_utc           = (Get-Date).ToUniversalTime().ToString("o")
    vps              = $remote
    vps_fix_exit     = $vpsEc
    cf_recommendation = "www.clinic.no1kmedi.com: Cloudflare proxied (orange) does not get Universal SSL on free plan for 4th-level names. Set A record www.clinic to DNS only (grey cloud) OR remove www.clinic and use https://clinic.no1kmedi.com only."
    probes           = $probes
}
$outPath = Join-Path $root "reports\no1kmedi_domain_recommended_ssl_fix_latest.json"
$out | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding utf8
Write-Host "Wrote $outPath"
if ($vpsEc -ne 0) { exit $vpsEc }
$fail = @($probes | Where-Object { -not $_.ok })
$wwwClinicOnly = ($fail.Count -eq 1) -and ($fail[0].url -eq "https://www.clinic.no1kmedi.com/")
if ($fail.Count -gt 0 -and -not $wwwClinicOnly) {
    Write-Host "Probe failures: $($fail.Count) — see reports\no1kmedi_domain_recommended_ssl_fix_latest.json"
    exit 2
}
if ($wwwClinicOnly) {
    Write-Host "VPS OK. www.clinic HTTPS needs Cloudflare: set A record www.clinic to DNS only (grey cloud), or use https://clinic.no1kmedi.com only."
}
exit 0
