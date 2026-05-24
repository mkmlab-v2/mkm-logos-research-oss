# Sync L3 production logos ANN sqlite (+ build report JSON) to Hostinger VPS monorepo artifacts.
# Topology: docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md (VPS=compute only; Cloudflare=DNS/proxy only).
# Prereq: OpenSSH scp/ssh; MKM_VPS_HOST + MKM_VPS_USER (see sync_showroom_to_vps.ps1 / .env).
# Does NOT reload PM2 or enable live trading.

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "",
    [string]$VpsUser = "",
    [string]$VpsRepoPath = "/opt/mkm-lab-workspace-v2",
    [switch]$DryRun,
    [switch]$SkipDotenvUserSync
)

$ErrorActionPreference = "Stop"
$syncDotenv = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1"
$dotenvPath = Join-Path $WorkspaceRoot ".env"
if (-not $SkipDotenvUserSync -and (Test-Path $syncDotenv) -and (Test-Path $dotenvPath)) {
    powershell -NoProfile -ExecutionPolicy Bypass -File $syncDotenv | Out-Null
}

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    return ""
}

if (-not $VpsHost) { $VpsHost = Get-EnvAny "MKM_VPS_HOST" }
if (-not $VpsUser) { $VpsUser = Get-EnvAny "MKM_VPS_USER" }
if (-not $VpsHost) { $VpsHost = "vps-mkmlife" }

$localSqlite = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_vector_index_ann_lite_v1.sqlite"
$localReport = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_vector_index_ann_lite_v1_latest.json"
$swapMeta = Join-Path $WorkspaceRoot "docs\final\artifacts\logos_rag_l3_production_swap_v1_latest.json"

foreach ($p in @($localSqlite, $swapMeta)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Missing required local artifact: $p (run apply_logos_rag_l3_production_st_index_v1.py first)."
    }
}

$remoteDir = "$VpsRepoPath/docs/final/artifacts"
$target = if ($VpsUser) { "${VpsUser}@${VpsHost}" } else { $VpsHost }
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"

Write-Host "[L3-VPS] target=$target remote=$remoteDir" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "[L3-VPS] DryRun: would ssh mkdir + scp sqlite + report" -ForegroundColor Yellow
    exit 0
}

$sshArgs = @()
if ($extra) { $sshArgs += $extra.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }
& ssh @sshArgs $target "mkdir -p $remoteDir"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$scpArgs = @()
if ($extra) { $scpArgs += $extra.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }
& scp @scpArgs $localSqlite "${target}:${remoteDir}/logos_vector_index_ann_lite_v1.sqlite"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (Test-Path -LiteralPath $localReport) {
    & scp @scpArgs $localReport "${target}:${remoteDir}/logos_vector_index_ann_lite_v1_latest.json"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& scp @scpArgs $swapMeta "${target}:${remoteDir}/logos_rag_l3_production_swap_v1_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[L3-VPS] OK synced L3 prod ANN artifacts" -ForegroundColor Green
exit 0
