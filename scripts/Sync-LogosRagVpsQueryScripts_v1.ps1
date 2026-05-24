# SCP minimal Logos ANN query scripts to VPS monorepo (for remote smoke / advisory).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "",
    [string]$VpsUser = "",
    [string]$VpsRepoPath = "/opt/mkm-lab-workspace-v2"
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

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

$target = if ($VpsUser) { "${VpsUser}@${VpsHost}" } else { $VpsHost }
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$scpArgs = @()
if ($extra) { $scpArgs += $extra.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }

$remoteScripts = "$VpsRepoPath/scripts"
& ssh @scpArgs $target "mkdir -p $remoteScripts"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$files = @(
    "scripts\query_logos_vector_index_ann_lite_v1.py",
    "scripts\logos_ann_lite_embedding_v1.py",
    "scripts\logos_vector_hash_stub_v1.py"
)
foreach ($rel in $files) {
    $loc = Join-Path $WorkspaceRoot $rel
    if (-not (Test-Path -LiteralPath $loc)) { throw "Missing: $loc" }
    $name = Split-Path -Leaf $loc
    & scp @scpArgs $loc "${target}:${remoteScripts}/$name"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "OK $name" -ForegroundColor Green
}
Write-Host "[RAG-VPS-SCRIPTS] OK" -ForegroundColor Cyan
exit 0
