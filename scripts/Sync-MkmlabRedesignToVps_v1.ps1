# Push mkmlab-redesign static site to Hostinger VPS web root (same host as jemaai / no1kmedi).
# DNS: Cloudflare proxy -> VPS (not hPanel shared hosting / public_html).
#
# Prereq: OpenSSH scp/ssh; MKM_VPS_HOST + MKM_VPS_USER (see sync_showroom_to_vps.ps1 / .env).
#
# Optional env:
#   MKMLAB_VPS_WEB_ROOT — default /var/www/mkmlab
#   MKM_VPS_SCP_EXTRA_ARGS — e.g. -i path\to\key
#   MKMLAB_VPS_RELOAD_NGINX — set 1 to run sudo nginx -t && reload after scp
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Sync-MkmlabRedesignToVps_v1.ps1
#   powershell ... -DryRun

param(
    [string]$WorkspaceRoot = "",
    [string]$SourceDir = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) { $WorkspaceRoot } else { Split-Path -Parent $PSScriptRoot }
if (-not $SourceDir) { $SourceDir = Join-Path $root "mkmlab-redesign" }

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

if (-not (Test-Path -LiteralPath (Join-Path $SourceDir "index.html"))) {
    Write-Error "Missing $SourceDir\index.html"
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if ([string]::IsNullOrWhiteSpace($hostName) -or [string]::IsNullOrWhiteSpace($user)) {
    throw "[mkmlab-vps-sync] set MKM_VPS_HOST and MKM_VPS_USER (Process or User env)."
}

$remoteRoot = Get-EnvAny "MKMLAB_VPS_WEB_ROOT"
if ([string]::IsNullOrWhiteSpace($remoteRoot)) { $remoteRoot = "/var/www/mkmlab" }
$remoteRoot = $remoteRoot.TrimEnd("/")
$dest = "${user}@${hostName}:${remoteRoot}/"

$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$extraArgs = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $extraArgs = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

$sourceTrail = (Join-Path $SourceDir "*").Replace("\", "/")
Write-Host "[mkmlab-vps-sync] source: $SourceDir"
Write-Host "[mkmlab-vps-sync] dest:   $dest"
Write-Host "[mkmlab-vps-sync] CF apex mkmlab.space must A/AAAA or CNAME to this VPS (not Hostinger parking hcdn)."

if ($DryRun) {
    Write-Host "[mkmlab-vps-sync] DRYRUN: scp -r $($extraArgs -join ' ') `"$SourceDir\*`" `"$dest`""
    exit 0
}

& scp @extraArgs -r (Join-Path $SourceDir "*") $dest
if ($LASTEXITCODE -ne 0) { throw "[mkmlab-vps-sync] scp failed: $LASTEXITCODE" }

$reload = Get-EnvAny "MKMLAB_VPS_RELOAD_NGINX"
if ($reload -eq "1") {
    $sshTarget = "${user}@${hostName}"
    & ssh @extraArgs $sshTarget "sudo nginx -t && sudo systemctl reload nginx"
    if ($LASTEXITCODE -ne 0) { throw "[mkmlab-vps-sync] nginx reload failed: $LASTEXITCODE" }
}

Write-Host "[mkmlab-vps-sync] OK"
exit 0
