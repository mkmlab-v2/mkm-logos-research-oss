#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$root = "c:\workspace"
$VpsRepoRoot = "/opt/mkm-destiny-ai-41e38ec6"

function Get-EnvAny([string]$Name) {
    $v = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    return [Environment]::GetEnvironmentVariable($Name, "User")
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshExtra = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $sshExtra = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}
$sshTarget = "${user}@${hostName}"

& scp @($sshExtra + @(
    (Join-Path $root "scripts\deploy\linux\apply_logos_trace_nginx_include.sh"),
    "${sshTarget}:${VpsRepoRoot}/scripts/deploy/linux/apply_logos_trace_nginx_include.sh"
))

$cmd = (
    "sudo cp -f /etc/nginx/sites-enabled/api.jemaai.cloud.bak.logos_trace.20260520T042915Z /etc/nginx/sites-enabled/api.jemaai.cloud 2>/dev/null || true; " +
    "sudo rm -f /etc/nginx/sites-enabled/api.jemaai.cloud.bak.logos_trace.*; " +
    "sed -i 's/\r$//' ${VpsRepoRoot}/scripts/deploy/linux/apply_logos_trace_nginx_include.sh; " +
    "sudo bash ${VpsRepoRoot}/scripts/deploy/linux/apply_logos_trace_nginx_include.sh; " +
    "curl -sS http://127.0.0.1:8021/health; echo; " +
    "curl -sS -k https://127.0.0.1/v1/logos/health -H 'Host: api.jemaai.cloud'; echo"
)

& ssh @($sshExtra + @($sshTarget, $cmd))
