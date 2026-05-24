# Remote KO Top-K query smoke against VPS prod ANN sqlite (B-track).
param(
    [string]$VpsHost = "",
    [string]$VpsUser = "",
    [string]$VpsRepoPath = "/opt/mkm-lab-workspace-v2",
    [string]$KoQuery = "위기 가운데 언약의 안정과 신실",
    [string]$ModelId = "sentence-transformers/all-MiniLM-L6-v2"
)

$ErrorActionPreference = "Stop"

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
$sshBase = @("-o", "ConnectTimeout=30")
if ($extra) { $sshBase += $extra.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }

$remoteArt = "$VpsRepoPath/docs/final/artifacts"
$sqlite = "$remoteArt/logos_vector_index_ann_lite_v1.sqlite"
$outLocal = "C:\workspace\docs\final\artifacts\logos_rag_vps_live_smoke_v1_latest.json"
$remoteScript = "/tmp/mkm_logos_rag_vps_smoke.sh"
$remoteOut = "/tmp/logos_rag_vps_query_smoke.json"

$koEsc = $KoQuery -replace "'", "'\''"
$sh = @(
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    "cd $VpsRepoPath",
    "SQL='$sqlite'",
    "test -f `"`$SQL`"",
    "PY=python3; command -v `$PY >/dev/null 2>&1 || PY=python",
    "PROBE=`$(`$PY -c `"import sqlite3; c=sqlite3.connect('`$SQL'); n=c.execute('select count(*) from logos_vec_stub').fetchone()[0]; m=c.execute('select embedding_mode from logos_vec_stub limit 1').fetchone()[0]; print('%s %s' % (n,m))`")",
    "ROWS=`$(echo `$PROBE | awk '{print `$1}')",
    "MODE=`$(echo `$PROBE | awk '{print `$2}')",
    "echo ROWS=`$ROWS MODE=`$MODE",
    "test `"`$ROWS`" -ge 30000",
    "test `"`$MODE`" = sentence_transformers_v1",
    "`$PY scripts/query_logos_vector_index_ann_lite_v1.py --sqlite `"`$SQL`" --query '$koEsc' --top-k 3 --sentence-transformer-model '$ModelId' --output-json $remoteOut",
    "cat $remoteOut"
) -join "`n"

$localSh = Join-Path $env:TEMP "mkm_logos_rag_vps_smoke_$([Guid]::NewGuid().ToString('N')).sh"
[System.IO.File]::WriteAllText($localSh, $sh + "`n", [System.Text.UTF8Encoding]::new($false))

Write-Host "[RAG-VPS-SMOKE] upload script -> $target" -ForegroundColor Cyan
$scpArgs = @() + $sshBase + $localSh, "${target}:${remoteScript}"
& scp @scpArgs
if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $localSh -Force -ErrorAction SilentlyContinue; exit $LASTEXITCODE }

$raw = & ssh @sshBase $target "chmod +x $remoteScript && bash $remoteScript" 2>&1 | Out-String
$code = $LASTEXITCODE
Remove-Item -LiteralPath $localSh -Force -ErrorAction SilentlyContinue

$lines = $raw -split "`r?`n"
$hits = @()
$rows = $null
$mode = $null
$qdoc = $null
foreach ($ln in $lines) {
    if ($ln -match '^ROWS=(\d+)\s+MODE=(\S+)') {
        $rows = [int]$Matches[1]
        $mode = $Matches[2]
    }
}
$m = [regex]::Match($raw, '\{\s*"schema":\s*"logos_vector_ann_lite_query_result_v1"[\s\S]*?\n\}')
if ($m.Success) {
    try {
        $qdoc = $m.Value | ConvertFrom-Json
        $hits = @($qdoc.top_k | ForEach-Object { $_.verse_id })
        if (-not $mode) { $mode = [string]$qdoc.embedding_mode }
    } catch { $qdoc = $null }
}
if ($hits.Count -lt 1) {
    $hits = @([regex]::Matches($raw, '"verse_id":\s*"([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Select-Object -First 3)
}
$ok = ($code -eq 0) -and ($hits.Count -ge 1) -and ($rows -ge 30000) -and ($mode -eq 'sentence_transformers_v1')

$doc = @{
    schema          = "logos_rag_vps_live_smoke_v1"
    ts_utc          = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tier = "B"
    research_only   = $true
    ok              = $ok
    vps_target      = $target
    remote_sqlite   = $sqlite
    index_rows      = $rows
    embedding_mode  = $mode
    ssh_exit_code   = $code
    query_ko        = $KoQuery
    model_id        = $ModelId
    top_hits        = $hits
    query_result_schema = if ($qdoc) { $qdoc.schema } else { $null }
    stdout_tail     = if ($raw.Length -gt 2500) { $raw.Substring($raw.Length - 2500) } else { $raw }
    track_wall      = @{
        non_gating           = $true
        pm2_reload           = $false
        a_track_live_trading = $false
    }
}
$doc | ConvertTo-Json -Depth 8 | Set-Content -Path $outLocal -Encoding utf8
Write-Host ($doc | ConvertTo-Json -Compress)
if (-not $ok) { exit 1 }
exit 0
