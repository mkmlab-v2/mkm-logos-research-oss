<#
.SYNOPSIS
  Guard-driven daily 1-page ops brief: refresh independent-lens JSON, fusion stub, thin report, then materialize Markdown.

.DESCRIPTION
  0) (optional) Independent lens runners — `myeongni` / `sasang` / `market_sasang` / `logos` → `docs/final/artifacts/*_latest.json` (fusion stub reads these; daily brief §1c embeds the same files)
  1) `report_independent_lens_fusion_stub_v0.py` — `independent_lens_fusion_stub_latest.json`
  2) (optional) Logos Track B commander deep report JSON + MD — separate from `run_lens_logos.py`
  2b) (optional) `emit_myeongni_thin_bridge_line_v1.py --calendar-date auto` — one-line myeongni JSONL aligned to the nearest `curated_dates_v1` day, then Thin uses `--myeongni-jsonl` (default on; `-SkipMyeongniThinBridge` restores stock overlap file)
  3) `eval_multilens_harness_v2_thin.py --populate-default-samples` — `multilens_eval_v2_thin_report_latest.json`
  3b) `myeongri_core_v2_upgrade.py` — `reports/myeongri_core_v2_upgrade_latest.json` (브리프 §1e; `-SkipMyeongriV2Upgrade` 생략)
  4) `build_daily_execution_insight_brief_v1.py` — `reports/daily_execution_insight_brief_latest.md`

  Template (human): projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md
#>
param(
    [string]$WorkspaceRoot = 'C:\workspace',
    [switch]$SkipIndependentLensRefresh,
    [switch]$SkipFusionRefresh,
    [switch]$SkipLogosTrackBDeepReport,
    [switch]$SkipThinRefresh,
    [switch]$SkipMyeongniThinBridge,
    [switch]$SkipMyeongriV2Upgrade,
    [switch]$DatedCopy,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$lensMyeongni = @('scripts\run_lens_myeongni.py')
$lensSasang = @('scripts\run_lens_sasang.py')
$lensMarketSasang = @('scripts\run_market_sasang_lens_v1.py')
$lensLogos = @('scripts\run_lens_logos.py')
$fusion = @('scripts\report_independent_lens_fusion_stub_v0.py')
$logosDeep = @('scripts\run_logos_track_b_commander_deep_report_v1.py')
$logosMd = @('scripts\materialize_logos_track_b_commander_deep_report_v1.py')
$thinOut = 'docs\final\artifacts\multilens_eval_v2_thin_report_latest.json'
$myeongniBridgeOut = 'data\multilens_eval\myeongni_independent_lens_thin_bridge_latest.jsonl'
$myeongriV2 = @('scripts\myeongri_core_v2_upgrade.py')
$briefArgs = @('scripts\build_daily_execution_insight_brief_v1.py')
if ($DatedCopy) { $briefArgs += '--also-dated-copy' }

if ($DryRun) {
    if (-not $SkipIndependentLensRefresh) {
        Write-Host ('py ' + ($lensMyeongni -join ' '))
        Write-Host ('py ' + ($lensSasang -join ' '))
        Write-Host ('py ' + ($lensMarketSasang -join ' '))
        Write-Host ('py ' + ($lensLogos -join ' '))
    }
    if (-not $SkipFusionRefresh) { Write-Host ('py ' + ($fusion -join ' ')) }
    if (-not $SkipLogosTrackBDeepReport) {
        Write-Host ('py ' + ($logosDeep -join ' '))
        Write-Host ('py ' + ($logosMd -join ' '))
    }
    if (-not $SkipThinRefresh) {
        if (-not $SkipMyeongniThinBridge) {
            Write-Host ('py scripts\emit_myeongni_thin_bridge_line_v1.py --calendar-date auto --out ' + $myeongniBridgeOut)
        }
        $t = @('scripts\eval_multilens_harness_v2_thin.py', '--populate-default-samples')
        if (-not $SkipMyeongniThinBridge) { $t += @('--myeongni-jsonl', $myeongniBridgeOut) }
        $t += @('--out', $thinOut)
        Write-Host ('py ' + ($t -join ' '))
    }
        if (-not $SkipMyeongriV2Upgrade) { Write-Host ('py ' + ($myeongriV2 -join ' ')) }
        Write-Host ('py ' + ($briefArgs -join ' '))
    exit 0
}

if (-not $SkipIndependentLensRefresh) {
    Write-Host '== independent lens JSON (myeongni -> sasang -> market_sasang -> logos) ==' -ForegroundColor Cyan
    & py @lensMyeongni
    if ($LASTEXITCODE -ne 0) { Write-Host 'WARN: run_lens_myeongni.py failed; fusion/brief may use stale myeongni JSON.' -ForegroundColor Yellow }
    & py @lensSasang
    if ($LASTEXITCODE -ne 0) { Write-Host 'WARN: run_lens_sasang.py failed; downstream market_sasang may be stale.' -ForegroundColor Yellow }
    & py @lensMarketSasang
    if ($LASTEXITCODE -ne 0) { Write-Host 'WARN: run_market_sasang_lens_v1.py failed.' -ForegroundColor Yellow }
    & py @lensLogos
    if ($LASTEXITCODE -ne 0) { Write-Host 'WARN: run_lens_logos.py failed; logos independent lens JSON may be stale.' -ForegroundColor Yellow }
}
if (-not $SkipFusionRefresh) {
    Write-Host '== fusion stub refresh ==' -ForegroundColor Cyan
    & py @fusion
    if ($LASTEXITCODE -ne 0) { throw "report_independent_lens_fusion_stub_v0.py failed: $LASTEXITCODE" }
}
if (-not $SkipLogosTrackBDeepReport) {
    Write-Host '== Logos Track B commander deep report (JSON + MD) ==' -ForegroundColor Cyan
    & py @logosDeep
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'WARN: run_logos_track_b_commander_deep_report_v1.py failed (missing logos lens?). Skip MD.' -ForegroundColor Yellow
    } else {
        & py @logosMd
        if ($LASTEXITCODE -ne 0) { throw "materialize_logos_track_b_commander_deep_report_v1.py failed: $LASTEXITCODE" }
    }
}
if (-not $SkipThinRefresh) {
    if (-not $SkipMyeongniThinBridge) {
        Write-Host '== myeongni thin bridge JSONL (auto grid snap) ==' -ForegroundColor Cyan
        & py (Join-Path $root 'scripts\emit_myeongni_thin_bridge_line_v1.py') @(
            '--calendar-date', 'auto',
            '--out', (Join-Path $root $myeongniBridgeOut)
        )
        if ($LASTEXITCODE -ne 0) { throw "emit_myeongni_thin_bridge_line_v1.py failed: $LASTEXITCODE" }
    }
    Write-Host '== multilens thin report (populated) ==' -ForegroundColor Cyan
    $thinArgs = @('scripts\eval_multilens_harness_v2_thin.py', '--populate-default-samples')
    if (-not $SkipMyeongniThinBridge) {
        $thinArgs += @('--myeongni-jsonl', (Join-Path $root $myeongniBridgeOut))
    }
    $thinArgs += @('--out', $thinOut)
    & py @thinArgs
    if ($LASTEXITCODE -ne 0) { throw "eval_multilens_harness_v2_thin.py failed: $LASTEXITCODE" }
}
if (-not $SkipMyeongriV2Upgrade) {
    Write-Host '== myeongri core v2 upgrade (jijangan / research shinsal / size reco) ==' -ForegroundColor Cyan
    & py @myeongriV2
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'WARN: myeongri_core_v2_upgrade.py failed; brief §1e may show missing v2 JSON.' -ForegroundColor Yellow
    }
}
Write-Host '== daily execution insight brief ==' -ForegroundColor Cyan
& py @briefArgs
if ($LASTEXITCODE -ne 0) { throw "build_daily_execution_insight_brief_v1.py failed: $LASTEXITCODE" }
Write-Host "OK: brief -> $root\reports\daily_execution_insight_brief_latest.md" -ForegroundColor Green
exit 0
