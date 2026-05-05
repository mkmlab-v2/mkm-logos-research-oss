# Stage-runner for full-canon global atom expansion bootstrap.
param(
    [string]$SeedInsightJson = "docs/final/artifacts/bible_meaning_insight_candidates_latest.json",
    [string]$VerseSourceJson = "data/logos/verse_4pipeline_full_31102.json",
    [string]$OutDir = "docs/final/artifacts/global_atom_full_canon",
    [switch]$FastSmoke,
    [switch]$UseVerseSource,
    [switch]$UseEventSource,
    [int]$EventWindowSize = 5,
    [string]$StartStage = "genesis",
    [string]$EndStage = "full_canon",
    [string]$ReportOutJson = "docs/final/artifacts/global_atom_full_canon_batch_report_latest.json"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

if ($FastSmoke) {
    $stagePlan = @(
        @{ stage = "genesis"; target_count = 64; min_similarity = 0.72 },
        @{ stage = "torah"; target_count = 96; min_similarity = 0.72 },
        @{ stage = "prophets"; target_count = 128; min_similarity = 0.73 },
        @{ stage = "gospels"; target_count = 96; min_similarity = 0.73 },
        @{ stage = "full_canon"; target_count = 160; min_similarity = 0.74 }
    )
} else {
    $stagePlan = @(
        @{ stage = "genesis"; target_count = 512; min_similarity = 0.70 },
        @{ stage = "torah"; target_count = 2048; min_similarity = 0.71 },
        @{ stage = "prophets"; target_count = 3072; min_similarity = 0.73 },
        @{ stage = "gospels"; target_count = 2048; min_similarity = 0.72 },
        @{ stage = "full_canon"; target_count = 4096; min_similarity = 0.75 }
    )
}

$stageOrder = @("genesis","torah","prophets","gospels","full_canon")
$startIdx = [Array]::IndexOf($stageOrder, $StartStage)
if ($startIdx -lt 0) {
    throw "Invalid -StartStage '$StartStage'. Allowed: genesis, torah, prophets, gospels, full_canon"
}
$endIdx = [Array]::IndexOf($stageOrder, $EndStage)
if ($endIdx -lt 0) {
    throw "Invalid -EndStage '$EndStage'. Allowed: genesis, torah, prophets, gospels, full_canon"
}
if ($endIdx -lt $startIdx) {
    throw "Invalid stage range: StartStage '$StartStage' must be before or equal to EndStage '$EndStage'"
}
$stagePlan = @($stagePlan | Where-Object {
    $idx = [Array]::IndexOf($stageOrder, $_.stage)
    $idx -ge $startIdx -and $idx -le $endIdx
})

$outDirAbs = Join-Path $workspaceRoot $OutDir
New-Item -ItemType Directory -Path $outDirAbs -Force | Out-Null

$runStamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$stages = @()
$index = 0
foreach ($p in $stagePlan) {
    $index += 1
    $stage = $p.stage
    $target = [int]$p.target_count
    $minSim = [double]$p.min_similarity

    Write-Host ("[{0}/{1}] stage={2}, target={3}, min_similarity={4}" -f $index, $stagePlan.Count, $stage, $target, $minSim) -ForegroundColor Cyan

    $inputJson = Join-Path $outDirAbs ("{0}_{1}_input.json" -f $runStamp, $stage)
    if ($UseEventSource) {
        & py "scripts/build_global_atom_full_canon_event_ingest_v1.py" `
            "--verse-source-json" $VerseSourceJson `
            "--stage" $stage `
            "--target-count" $target `
            "--window-size" $EventWindowSize `
            "--output-json" $inputJson
    } elseif ($UseVerseSource) {
        & py "scripts/build_global_atom_full_canon_verse_ingest_v1.py" `
            "--verse-source-json" $VerseSourceJson `
            "--stage" $stage `
            "--target-count" $target `
            "--output-json" $inputJson
    } else {
        & py "scripts/build_global_atom_full_canon_batch_input_v1.py" `
            "--seed-insight-json" $SeedInsightJson `
            "--stage" $stage `
            "--target-count" $target `
            "--output-json" $inputJson
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $nodesJsonl = Join-Path $outDirAbs ("{0}_{1}_nodes.jsonl" -f $runStamp, $stage)
    $edgesJsonl = Join-Path $outDirAbs ("{0}_{1}_edges.jsonl" -f $runStamp, $stage)
    $matrixJson = Join-Path $outDirAbs ("{0}_{1}_similarity_matrix.json" -f $runStamp, $stage)
    $phaseJson = Join-Path $outDirAbs ("{0}_{1}_phase_report.json" -f $runStamp, $stage)

    if ($target -le 2048) {
        & py "scripts/build_global_atom_network_v1.py" `
            "--insight-json" $inputJson `
            "--top-n" $target `
            "--min-similarity" $minSim `
            "--nodes-out-jsonl" $nodesJsonl `
            "--edges-out-jsonl" $edgesJsonl `
            "--matrix-out-json" $matrixJson `
            "--phase-report-out-json" $phaseJson `
            "--max-edges" 2000000 `
            "--write-matrix"
    } else {
        & py "scripts/build_global_atom_network_v1.py" `
            "--insight-json" $inputJson `
            "--top-n" $target `
            "--min-similarity" $minSim `
            "--nodes-out-jsonl" $nodesJsonl `
            "--edges-out-jsonl" $edgesJsonl `
            "--matrix-out-json" $matrixJson `
            "--phase-report-out-json" $phaseJson `
            "--max-edges" 2000000
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $stages += @{
        stage = $stage
        target_count = $target
        min_similarity = $minSim
        input_json = $inputJson
        nodes_jsonl = $nodesJsonl
        edges_jsonl = $edgesJsonl
        matrix_json = $matrixJson
        phase_report_json = $phaseJson
    }
}

$manifest = @{
    schema = "global_atom_full_canon_batch_manifest_v1"
    generated_at_utc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    research_only = $true
    promotion_required = $true
    source_track = "K"
    run_stamp = $runStamp
    out_dir = $outDirAbs
    fast_smoke = [bool]$FastSmoke
    use_verse_source = [bool]$UseVerseSource
    use_event_source = [bool]$UseEventSource
    event_window_size = $EventWindowSize
    verse_source_json = $VerseSourceJson
    seed_insight_json = $SeedInsightJson
    start_stage = $StartStage
    end_stage = $EndStage
    stages = $stages
}
$manifestJson = Join-Path $outDirAbs ("{0}_manifest.json" -f $runStamp)
($manifest | ConvertTo-Json -Depth 8) + "`n" | Out-File -FilePath $manifestJson -Encoding utf8
Write-Host ("[manifest] {0}" -f $manifestJson) -ForegroundColor DarkGray

Write-Host "[report] build integrated batch report" -ForegroundColor Cyan
& py "scripts/build_global_atom_full_canon_batch_report_v1.py" `
    "--stages-json" $manifestJson `
    "--output-json" $ReportOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: global atom full-canon staged batch bootstrap complete." -ForegroundColor Green

