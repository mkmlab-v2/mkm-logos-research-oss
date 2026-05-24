# MKM Hostinger + Cloudflare topology gate (local files + optional SSH IP compare)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, 'Process')
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, 'User')
    if ($v) { return $v.Trim() }
    return ''
}

$hostFqdn = Get-EnvAny 'MKM_VPS_HOST'
$extra = @()
if (-not $hostFqdn) {
    py scripts/check_mkm_hostinger_cloudflare_topology_v1.py
    exit $LASTEXITCODE
}

$argsList = @('scripts/check_mkm_hostinger_cloudflare_topology_v1.py', '--ssh-compare', '--ssh-fqdn', $hostFqdn)
py @argsList
exit $LASTEXITCODE
