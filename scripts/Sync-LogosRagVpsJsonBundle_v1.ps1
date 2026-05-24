# SCP Logos RAG JSON/pilot bundle to VPS (after L3 sqlite sync).
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

$remoteArt = "$VpsRepoPath/docs/final/artifacts"
$remotePilot = "$VpsRepoPath/reports/constitution/btrack_pilot"
& ssh @scpArgs $target "mkdir -p $remoteArt $remotePilot"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$art = Join-Path $WorkspaceRoot "docs\final\artifacts"
$pilot = Join-Path $WorkspaceRoot "reports\constitution\btrack_pilot"
$files = @(
    @{ L = Join-Path $art "semantic_rag_bridge_insight_bundle_v1_latest.json"; R = "$remoteArt/semantic_rag_bridge_insight_bundle_v1_latest.json" },
    @{ L = Join-Path $art "logos_rag_btrack_promotion_gate_v1_latest.json"; R = "$remoteArt/logos_rag_btrack_promotion_gate_v1_latest.json" },
    @{ L = Join-Path $art "logos_rag_l2_post_ingest_v1_latest.json"; R = "$remoteArt/logos_rag_l2_post_ingest_v1_latest.json" },
    @{ L = Join-Path $art "logos_rag_l3_readiness_v1_latest.json"; R = "$remoteArt/logos_rag_l3_readiness_v1_latest.json" },
    @{ L = Join-Path $art "logos_semantic_query_set_v4_ko_en_v1.json"; R = "$remoteArt/logos_semantic_query_set_v4_ko_en_v1.json" },
    @{ L = Join-Path $pilot "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"; R = "$remotePilot/philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json" }
)

foreach ($f in $files) {
    if (-not (Test-Path -LiteralPath $f.L)) {
        Write-Host "SKIP missing: $($f.L)" -ForegroundColor Yellow
        continue
    }
    & scp @scpArgs $f.L "${target}:$($f.R)"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "OK $($f.R)" -ForegroundColor Green
}
Write-Host "[RAG-VPS-JSON] bundle OK" -ForegroundColor Cyan
exit 0
