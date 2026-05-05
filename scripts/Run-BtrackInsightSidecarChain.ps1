# B-track insight sidecar chain: optional NotebookLM KPI refresh -> sidecar -> lens agreement -> inventory -> bridge index -> optional signoff.
# Run from repo root (or any cwd; resolves workspace from script location).
# Daily Windows task: scripts/register_btrack_insight_sidecar_chain_task.ps1 (default -SkipSignoff for unattended).
# Codebook/codepack-only path (drift strict + inventory + bridge + signoff): scripts/Run-BtrackCodebookCodepackPromotionChain.ps1
# After sidecar: scripts/build_btrack_prophecy_score_insight_overlay_view_v1.py (phase-3 observation join; not a gate input).

param(
    [switch]$SkipSignoff,
    [switch]$SkipNotebooklmKpi,
    [switch]$IncludeMultilensRefresh
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location -LiteralPath $root

Write-Host "check_codebook_codepack_drift_v1.py --strict (gate before sidecar/signoff)" -ForegroundColor DarkGray
& py "scripts/check_codebook_codepack_drift_v1.py" --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipNotebooklmKpi) {
    $mega = Join-Path $root "reports\notebooklm\btrack_mega_insights_10gb.jsonl"
    if (Test-Path -LiteralPath $mega) {
        Write-Host "NotebookLM KPI: report_btrack_notebooklm_jsonl_kpi.py" -ForegroundColor DarkGray
        & py "scripts/report_btrack_notebooklm_jsonl_kpi.py"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "Skip NotebookLM KPI (mega jsonl not present)." -ForegroundColor DarkGray
    }
}

if ($IncludeMultilensRefresh) {
    $logosBatch = Join-Path $root "data\logos\4lens_batch_sample.json"
    $logosFixture = Join-Path $root "tests\fixtures\logos_4lens_batch_minimal_v1.json"
    Write-Host "Multilens refresh: run_lens_logos.py" -ForegroundColor DarkGray
    if (Test-Path -LiteralPath $logosBatch) {
        & py "scripts/run_lens_logos.py" --batch-json $logosBatch
    } elseif (Test-Path -LiteralPath $logosFixture) {
        Write-Host "Logos: using tracked fixture (no data/logos/4lens_batch_sample.json)" -ForegroundColor DarkYellow
        & py "scripts/run_lens_logos.py" --batch-json $logosFixture
    } else {
        & py "scripts/run_lens_logos.py" --allow-fallback
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    foreach ($script in @("scripts/run_lens_myeongni.py", "scripts/run_lens_sasang.py")) {
        Write-Host "Multilens refresh: $script" -ForegroundColor DarkGray
        & py $script
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host "build_btrack_prophecy_score_insight_sidecar_stub_v1.py" -ForegroundColor DarkGray
& py "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "build_btrack_prophecy_score_insight_overlay_view_v1.py" -ForegroundColor DarkGray
& py "scripts/build_btrack_prophecy_score_insight_overlay_view_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "eval_btrack_insight_sidecar_lens_hit_agreement_v1.py" -ForegroundColor DarkGray
& py "scripts/eval_btrack_insight_sidecar_lens_hit_agreement_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "build_btrack_insight_bridge_inventory_v1.py" -ForegroundColor DarkGray
& py "scripts/build_btrack_insight_bridge_inventory_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "build_btrack_insight_promotion_bridge_index_v1.py" -ForegroundColor DarkGray
& py "scripts/build_btrack_insight_promotion_bridge_index_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipSignoff) {
    Write-Host "build_btrack_promotion_signoff_packet_v1.py --separate-track-gates" -ForegroundColor DarkGray
    & py "scripts/build_btrack_promotion_signoff_packet_v1.py" --separate-track-gates
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "build_sasang_interpretive_insight_bundle_v1.py (v1.1 reference bundle + synthesis; human-only decisions)" -ForegroundColor DarkGray
& py "scripts/build_sasang_interpretive_insight_bundle_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK B-track insight sidecar chain." -ForegroundColor Green
exit 0
