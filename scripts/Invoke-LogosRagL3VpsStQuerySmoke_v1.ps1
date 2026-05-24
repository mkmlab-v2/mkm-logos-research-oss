# L3 prod ANN: remote ST query smoke on Hostinger VPS (B-track, non-gating)
# Prereq: Sync-LogosRagL3ProdIndexToVps_v1.ps1 · ssh alias vps-mkmlife or MKM_VPS_HOST
param(
    [string]$SshTarget = 'vps-mkmlife',
    [string]$VpsRepoPath = '/opt/mkm-lab-workspace-v2',
    [string]$Query = 'God word',
    [string]$Model = 'paraphrase-multilingual-MiniLM-L12-v2',
    [int]$TopK = 3,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$out = Join-Path $root 'reports/logos_rag_l3_vps_st_query_smoke_latest.json'

$qEsc = $Query -replace "'", "'\''"
$remoteCmd = "cd $VpsRepoPath && test -f docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite && python3 scripts/query_logos_vector_index_ann_lite_v1.py --sqlite docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite --query '$qEsc' --top-k $TopK --sentence-transformer-model $Model"

Write-Host "[L3-VPS-ST] target=$SshTarget" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "DRYRUN: ssh $SshTarget $remoteCmd"
    exit 0
}

$prevEa = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$raw = & ssh.exe -o BatchMode=yes -o ConnectTimeout=20 -o LogLevel=ERROR $SshTarget $remoteCmd 2>&1 | Out-String
$code = $LASTEXITCODE
$ErrorActionPreference = $prevEa
if ($code -ne 0) {
    Write-Host $raw
    exit $LASTEXITCODE
}

$jsonStart = $raw.IndexOf('{')
if ($jsonStart -lt 0) {
    Write-Host $raw
    throw 'No JSON in remote stdout'
}
$payload = $raw.Substring($jsonStart) | ConvertFrom-Json
$doc = @{
    schema           = 'logos_rag_l3_vps_st_query_smoke_v1'
    ts_utc           = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    ok               = $true
    ssh_target       = $SshTarget
    vps_repo_path    = $VpsRepoPath
    query            = $Query
    model            = $Model
    remote_result    = $payload
    hypothesis_tier  = 'B'
    research_only    = $true
    track_wall       = @{
        pm2_reload          = $false
        a_track_live_trading = $false
    }
}
$doc | ConvertTo-Json -Depth 8 | Set-Content -Path $out -Encoding utf8
Write-Host "OK top1=$($payload.top_k[0].verse_id) score=$($payload.top_k[0].score) -> $out" -ForegroundColor Green
exit 0
