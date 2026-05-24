# RAG L3 VPS live ops: parallel artifact sync + remote ANN query smoke (B-track, NON_GATING).
# Topology: docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md
# Does NOT: PM2 reload, live trading, Track A promotion.

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "",
    [string]$VpsUser = "",
    [string]$VpsRepoPath = "/opt/mkm-lab-workspace-v2",
    [switch]$DryRun,
    [switch]$SkipSqliteSync,
    [switch]$SkipRemoteQuery,
    [switch]$SkipDotenvUserSync
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

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

$target = if ($VpsUser) { "${VpsUser}@${VpsHost}" } else { $VpsHost }
$extraRaw = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
$sshExtra = @()
if ($extraRaw) { $sshExtra += $extraRaw.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }

$art = Join-Path $WorkspaceRoot "docs\final\artifacts"
$pilot = Join-Path $WorkspaceRoot "reports\constitution\btrack_pilot"
$remoteArt = "$VpsRepoPath/docs/final/artifacts"
$remotePilot = "$VpsRepoPath/reports/constitution/btrack_pilot"

$requiredLocal = @(
    (Join-Path $art "logos_vector_index_ann_lite_v1.sqlite"),
    (Join-Path $art "logos_rag_l3_production_swap_v1_latest.json")
)
foreach ($p in $requiredLocal) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Missing required local artifact: $p (run apply_logos_rag_l3_production_st_index_v1.py first)."
    }
}

$jsonBundle = @(
    @{ Local = Join-Path $art "logos_vector_index_ann_lite_v1_latest.json"; Remote = "$remoteArt/logos_vector_index_ann_lite_v1_latest.json" },
    @{ Local = Join-Path $art "logos_rag_l3_production_swap_v1_latest.json"; Remote = "$remoteArt/logos_rag_l3_production_swap_v1_latest.json" },
    @{ Local = Join-Path $art "semantic_rag_bridge_insight_bundle_v1_latest.json"; Remote = "$remoteArt/semantic_rag_bridge_insight_bundle_v1_latest.json" },
    @{ Local = Join-Path $art "logos_rag_btrack_promotion_gate_v1_latest.json"; Remote = "$remoteArt/logos_rag_btrack_promotion_gate_v1_latest.json" },
    @{ Local = Join-Path $art "logos_rag_l2_post_ingest_v1_latest.json"; Remote = "$remoteArt/logos_rag_l2_post_ingest_v1_latest.json" },
    @{ Local = Join-Path $art "logos_rag_l3_readiness_v1_latest.json"; Remote = "$remoteArt/logos_rag_l3_readiness_v1_latest.json" },
    @{ Local = Join-Path $art "logos_semantic_query_set_v4_ko_en_v1.json"; Remote = "$remoteArt/logos_semantic_query_set_v4_ko_en_v1.json" },
    @{ Local = Join-Path $pilot "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"; Remote = "$remotePilot/philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json" }
)

$tsUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$outSync = Join-Path $art "logos_rag_l3_vps_sync_v1_latest.json"
$outSmoke = Join-Path $art "logos_rag_vps_live_smoke_v1_latest.json"
$modelId = "sentence-transformers/all-MiniLM-L6-v2"
$koQuery = "위기 가운데 언약의 안정과 신실"

Write-Host "[RAG-VPS] target=$target repo=$VpsRepoPath" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[RAG-VPS] DryRun: would mkdir, scp sqlite (unless Skip), scp JSON bundle, ssh query smoke" -ForegroundColor Yellow
    exit 0
}

function Invoke-ScpFile([string]$local, [string]$remote) {
    if (-not (Test-Path -LiteralPath $local)) {
        return @{ ok = $false; skipped = $true; local = $local }
    }
    $scpArgs = @()
    if ($sshExtra) { $scpArgs += $sshExtra }
    & scp @scpArgs $local "${target}:${remote}"
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $local -> $remote (exit $LASTEXITCODE)" }
    return @{ ok = $true; local = $local; remote = $remote }
}

& ssh @sshExtra $target "mkdir -p $remoteArt $remotePilot"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$stepResults = @()

# Wave A: L3 sqlite (delegates to Sync-LogosRagL3ProdIndexToVps) then JSON bundle script
if (-not $SkipSqliteSync) {
    $l3Script = Join-Path $WorkspaceRoot "scripts\Sync-LogosRagL3ProdIndexToVps_v1.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $l3Script -WorkspaceRoot $WorkspaceRoot -VpsHost $VpsHost -VpsUser $VpsUser -VpsRepoPath $VpsRepoPath -SkipDotenvUserSync
    $stepResults += @{ step = "l3_sqlite_sync"; exit_code = $LASTEXITCODE }
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL l3_sqlite_sync" -ForegroundColor Red }
}

$jsonScript = Join-Path $WorkspaceRoot "scripts\Sync-LogosRagVpsJsonBundle_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $jsonScript -WorkspaceRoot $WorkspaceRoot -VpsHost $VpsHost -VpsUser $VpsUser -VpsRepoPath $VpsRepoPath
$stepResults += @{ step = "json_bundle"; exit_code = $LASTEXITCODE }
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL json_bundle" -ForegroundColor Red }

$syncFailed = @($stepResults | Where-Object { $_.exit_code -ne 0 } | ForEach-Object { $_.step })
$filesSynced = @(
    "logos_vector_index_ann_lite_v1.sqlite"
) + @($jsonBundle | Where-Object { Test-Path -LiteralPath $_.Local } | ForEach-Object { Split-Path -Leaf $_.Local })

$syncDoc = @{
    schema              = "logos_rag_l3_vps_sync_v1"
    ts_utc              = $tsUtc
    hypothesis_tier     = "B"
    research_only       = $true
    ok                  = ($syncFailed.Count -eq 0)
    vps_target          = $target
    topology_note       = "Hostinger VPS compute only; Cloudflare DNS/proxy edge only"
    remote_artifacts_dir = $remoteArt
    remote_pilot_dir    = $remotePilot
    files_synced        = $filesSynced
    failed_steps        = $syncFailed
    track_wall          = @{
        pm2_reload          = $false
        a_track_live_trading = $false
        note                = "Artifact copy + optional remote query smoke; not live trading."
    }
}
$syncDoc | ConvertTo-Json -Depth 8 | Set-Content -Path $outSync -Encoding utf8

if ($syncFailed.Count -gt 0) {
    Write-Host "[RAG-VPS] sync FAILED: $($syncFailed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "[RAG-VPS] sync OK -> $outSync" -ForegroundColor Green

# Wave B: query scripts + remote smoke (delegated scripts)
$scriptsSync = Join-Path $WorkspaceRoot "scripts\Sync-LogosRagVpsQueryScripts_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $scriptsSync -WorkspaceRoot $WorkspaceRoot -VpsHost $VpsHost -VpsUser $VpsUser -VpsRepoPath $VpsRepoPath
if ($LASTEXITCODE -ne 0) { exit 1 }

if (-not $SkipRemoteQuery) {
    $smokeScript = Join-Path $WorkspaceRoot "scripts\Invoke-LogosRagVpsRemoteQuerySmoke_v1.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $smokeScript -VpsHost $VpsHost -VpsUser $VpsUser -VpsRepoPath $VpsRepoPath
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

Write-Host "[RAG-VPS] LIVE OK -> $outSync (+ logos_rag_vps_live_smoke_v1_latest.json)" -ForegroundColor Green
exit 0
