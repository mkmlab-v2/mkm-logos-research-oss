# Recover nginx after partial deploy: HTTP research + portal + mkmlab 301.
param([string]$WorkspaceRoot = "C:\workspace")
$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "srv1101456.hstgr.cloud" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"
$sshArgs = @()
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

$vpsRepo = "/opt/mkm-destiny-ai-41e38ec6"
$linux = Join-Path $root "scripts\deploy\linux"
$files = @(
    "apply_research_no1kmedi_nginx_http_only_v1.sh",
    "apply_no1kmedi_com_portal_http_only_v1.sh",
    "apply_mkmlab_space_retire_http_only_v1.sh"
)

& ssh @($sshArgs + @($remote, "mkdir -p $vpsRepo/scripts/deploy/linux"))
foreach ($f in $files) {
    & scp @($sshArgs + @((Join-Path $linux $f), "${remote}:${vpsRepo}/scripts/deploy/linux/"))
}

$cmd = @"
for f in /etc/nginx/sites-enabled/*; do
  if grep -q 'letsencrypt/live/no1kmedi.com/fullchain' "\$f" 2>/dev/null; then
    if [ ! -f /etc/letsencrypt/live/no1kmedi.com/fullchain.pem ]; then
      rm -f "\$f"
      echo "removed broken site: \$f"
    fi
  fi
done
if [ -f /etc/nginx/sites-available/research.no1kmedi.com ] && grep -q 'research.no1kmedi.com/fullchain' /etc/nginx/sites-available/research.no1kmedi.com 2>/dev/null; then
  if [ ! -f /etc/letsencrypt/live/research.no1kmedi.com/fullchain.pem ]; then
    rm -f /etc/nginx/sites-enabled/research.no1kmedi.com
    echo "removed broken research ssl vhost"
  fi
fi
export SKIP_NGINX_TEST=1
bash $vpsRepo/scripts/deploy/linux/apply_research_no1kmedi_nginx_http_only_v1.sh -y
bash $vpsRepo/scripts/deploy/linux/apply_no1kmedi_com_portal_http_only_v1.sh -y
bash $vpsRepo/scripts/deploy/linux/apply_mkmlab_space_retire_http_only_v1.sh -y
nginx -t && systemctl reload nginx
pm2 restart no1kmedi-com || true
echo RECOVER_OK
"@ -replace "`r`n", "`n"

& ssh @($sshArgs + @($remote, $cmd))
exit $LASTEXITCODE
