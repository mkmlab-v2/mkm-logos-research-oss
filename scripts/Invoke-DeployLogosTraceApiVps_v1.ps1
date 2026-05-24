#Requires -Version 5.1
<#
.SYNOPSIS
  VPS: install logos trace systemd + nginx snippet + reload (requires monorepo on host).
#>
param(
    [string]$WorkspaceRoot = "c:\workspace",
    [string]$VpsRepoRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [switch]$DryRun,
    [switch]$SkipNginxReload
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $WorkspaceRoot).Path
Set-Location $root

function Get-EnvAny([string]$Name) {
    $v = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v }
    return [Environment]::GetEnvironmentVariable($Name, "User")
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
$user = Get-EnvAny "MKM_VPS_USER"
if ([string]::IsNullOrWhiteSpace($hostName) -or [string]::IsNullOrWhiteSpace($user)) {
    throw "Set MKM_VPS_HOST and MKM_VPS_USER"
}

$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshExtra = @()
if (-not [string]::IsNullOrWhiteSpace($extraRaw)) {
    $sshExtra = $extraRaw -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

$sshTarget = "${user}@${hostName}"

$syncPairs = @(
    @{ Local = "scripts\logos_trace_api_stub_v1.py"; Remote = "${VpsRepoRoot}/scripts/logos_trace_api_stub_v1.py" },
    @{ Local = "scripts\compute_logos_reasoning_path_v1.py"; Remote = "${VpsRepoRoot}/scripts/compute_logos_reasoning_path_v1.py" },
    @{ Local = "scripts\deploy\linux\install_logos_trace_api_stub_systemd.sh"; Remote = "${VpsRepoRoot}/scripts/deploy/linux/install_logos_trace_api_stub_systemd.sh" },
    @{ Local = "scripts\deploy\linux\mkm-logos-trace-api-stub.service"; Remote = "${VpsRepoRoot}/scripts/deploy/linux/mkm-logos-trace-api-stub.service" },
    @{ Local = "scripts\deploy\linux\logos-trace-api.env.example"; Remote = "${VpsRepoRoot}/scripts/deploy/linux/logos-trace-api.env.example" },
    @{ Local = "scripts\deploy\linux\nginx-logos-trace-api.conf.example"; Remote = "${VpsRepoRoot}/scripts/deploy/linux/nginx-logos-trace-api.conf.example" },
    @{ Local = "scripts\deploy\linux\apply_logos_trace_nginx_include.sh"; Remote = "${VpsRepoRoot}/scripts/deploy/linux/apply_logos_trace_nginx_include.sh" }
)

function Invoke-ScpFile([string]$LocalRel, [string]$RemotePath) {
    $localPath = Join-Path $root $LocalRel
    if (-not (Test-Path -LiteralPath $localPath)) {
        throw "Missing local file: $localPath"
    }
    $remoteDir = ($RemotePath -replace "/[^/]+$", "")
    & ssh @($sshExtra + @($sshTarget, "mkdir -p '$remoteDir'"))
    if ($LASTEXITCODE -ne 0) { throw "ssh mkdir failed: $remoteDir" }
    $argv = @()
    foreach ($a in $sshExtra) { $argv += $a }
    $argv += $localPath
    $argv += "${sshTarget}:${RemotePath}"
    & scp @argv
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $LocalRel -> $RemotePath" }
}

$installRemote = (
    "set -e; " +
    "if [ ! -d '${VpsRepoRoot}/scripts' ]; then echo MISSING_REPO:${VpsRepoRoot} >&2; exit 2; fi; " +
    "cd '${VpsRepoRoot}'; " +
    "if command -v git >/dev/null 2>&1 && [ -d .git ]; then git pull --ff-only 2>/dev/null || true; fi; " +
    "export WORKSPACE_ROOT='${VpsRepoRoot}'; " +
    "sed -i 's/\r$//' scripts/deploy/linux/install_logos_trace_api_stub_systemd.sh scripts/deploy/linux/mkm-logos-trace-api-stub.service; " +
    "sudo -E bash scripts/deploy/linux/install_logos_trace_api_stub_systemd.sh"
)

if ($DryRun) {
    Write-Host "DRYRUN ssh $sshTarget $installRemote"
    exit 0
}

Write-Host "== [1/4] scp logos trace scripts to VPS repo ==" -ForegroundColor Cyan
foreach ($pair in $syncPairs) {
    if ($DryRun) {
        Write-Host "DRYRUN scp $($pair.Local) -> $($pair.Remote)"
        continue
    }
    Invoke-ScpFile -LocalRel $pair.Local -RemotePath $pair.Remote
}

Write-Host "== [2/4] install logos trace stub on VPS ==" -ForegroundColor Cyan
& ssh @($sshExtra + @($sshTarget, $installRemote))
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== [3/4] ensure api.jemaai includes logos trace snippet ==" -ForegroundColor Cyan
$includeSnip = (
    "sed -i 's/\r$//' ${VpsRepoRoot}/scripts/deploy/linux/apply_logos_trace_nginx_include.sh; " +
    "sudo bash ${VpsRepoRoot}/scripts/deploy/linux/apply_logos_trace_nginx_include.sh"
)
if ($DryRun) {
    Write-Host "DRYRUN ssh $sshTarget $includeSnip"
} else {
    & ssh @($sshExtra + @($sshTarget, $includeSnip))
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "nginx include step failed — add include /etc/nginx/snippets/mkm_logos_trace_api.conf; manually"
    }
}

if (-not $SkipNginxReload) {
    Write-Host "== [4/4] push showroom nginx snippet (oracle v6) ==" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\sync_showroom_to_vps.ps1") -ApplyRecommendedNginx
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Done. Probe: curl -sS https://api.jemaai.cloud/v1/logos/health" -ForegroundColor Green
