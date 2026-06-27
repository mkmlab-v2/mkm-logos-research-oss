# Publish magic_orb_question_insight_v1 + graph_bloom ([HYPO] B-track).
param(
    [string]$Query = "",
    [string]$QueryId = "q01",
    [switch]$ExpandGraph,
    [switch]$Batch,
    [switch]$ExpandPrimaryOnly,
    [switch]$SyncPublic = $true,
    [switch]$VerifyAssets,
    [switch]$DeployMkmlife,
    [switch]$PushKv,
    [switch]$LiveSmoke,
    [switch]$RebuildInsight,
    [switch]$SkipOracleSphereHero,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { "C:\workspace" }
Set-Location $root

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

function Get-MagicOrbQueryFromFixture {
    param([string]$Id)
    $fixture = Join-Path $root "docs\final\fixtures\magic_orb_question_insight_queries_v1.json"
    if (-not (Test-Path -LiteralPath $fixture)) { return $null }
    $doc = Get-Content -LiteralPath $fixture -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($item in @($doc.items)) {
        if ($item.id -eq $Id) { return [string]$item.query_ko }
    }
    return $null
}

$fixtureQuery = Get-MagicOrbQueryFromFixture -Id $QueryId
if ($fixtureQuery) {
    $Query = $fixtureQuery
} elseif (-not $Query) {
    $Query = "위기 가운데 언약의 안정과 신실"
}

$queryFile = Join-Path $env:TEMP "mkm_magic_orb_query_$QueryId.txt"
[System.IO.File]::WriteAllText($queryFile, $Query, [System.Text.UTF8Encoding]::new($false))
$env:PYTHONUTF8 = "1"

if ($Batch) {
    $batchArgs = @("-3", "scripts/run_magic_orb_question_insight_batch_v1.py", "--primary-query-id", $QueryId)
    if ($ExpandGraph) { $batchArgs += "--expand-graph" }
    elseif ($ExpandPrimaryOnly) { $batchArgs += "--expand-primary-only" }
    if ($DryRun) { $batchArgs += "--dry-run" }
    & $py @batchArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "OK: batch -> reports/magic_orb_question_insight_query_batch_v1_latest.json + public/data/magic_orb_insight_by_query/*.json" -ForegroundColor Green
    if (-not $VerifyAssets -and -not $DeployMkmlife -and -not $PushKv -and -not $LiveSmoke) { exit 0 }
}

$deployOnly = $DeployMkmlife -or $LiveSmoke -or $PushKv -or $VerifyAssets
$runSingleChain = (-not $Batch) -and ($RebuildInsight -or -not $deployOnly)

$chainArgs = @(
    "-3", "scripts/run_question_semantic_rag_bridge_chain_v1.py",
    "--query-file", $queryFile,
    "--query-id", $QueryId,
    "--skip-ann-lite"
)
if ($ExpandGraph -or $QueryId -like "job_*") { $chainArgs += "--expand-graph" }
if ($SyncPublic) { $chainArgs += "--sync-public" }
if ($DryRun) { $chainArgs += "--dry-run" }

if ($runSingleChain) {
    & $py @chainArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not $DryRun) {
        $validateArgs = @("-3", "scripts/validate_magic_orb_four_slot_v1.py")
        $isJobQuery = ($QueryId -in @("job_suffering_reason", "job_prologue_suffering")) -or ($Query -match "욥|job")
        if (-not $isJobQuery) { $validateArgs += "--allow-missing-four-slot" }
        & $py @validateArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host "OK: insight -> docs/final/artifacts + projects/mkm/mkm-life/public/data (if -SyncPublic)" -ForegroundColor Green
} elseif (-not $Batch -and $deployOnly -and -not $RebuildInsight) {
    Write-Host "Skip: single-query chain (deploy/smoke/verify only; use -RebuildInsight to regenerate q01 insight)" -ForegroundColor DarkGray
}

if ($VerifyAssets) {
    & $py scripts/verify_magic_orb_graph_bloom_assets_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$mkm = Join-Path $root "projects\mkm\mkm-life"
if ($DeployMkmlife) {
    if ($DryRun) {
        Write-Host "[DRY] Deploy-CloudflareMkmlife.ps1" -ForegroundColor Yellow
    } else {
        $deployArgs = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", (Join-Path $mkm "scripts\Deploy-CloudflareMkmlife.ps1")
        )
        if ($SkipOracleSphereHero) { $deployArgs += "-SkipOracleSphereHero" }
        & powershell @deployArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

if ($PushKv) {
  $kvArgs = @("-File", (Join-Path $root "scripts\Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1"))
  if ($DryRun) { $kvArgs += "-DryRun" }
  & powershell -NoProfile -ExecutionPolicy Bypass @kvArgs
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($LiveSmoke) {
    & $py scripts/probe_mkmlife_magic_orb_live_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Push-Location $mkm
    try {
        node scripts/smoke-magic-orb-oracle-sphere-live.mjs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

if (-not $DeployMkmlife -and -not $PushKv -and -not $LiveSmoke) {
    Write-Host "Next: -DeployMkmlife -PushKv -LiveSmoke or -Batch -ExpandGraph; deploy-only skips chain (use -RebuildInsight)" -ForegroundColor Cyan
}
