<#
.SYNOPSIS
  Guard-driven daily 1-page ops brief: refresh fusion stub + thin report, then materialize Markdown.

.DESCRIPTION
  1) `report_independent_lens_fusion_stub_v0.py` — `independent_lens_fusion_stub_latest.json`
  2) (optional) Logos Track B commander deep report JSON + MD — disk artifacts must exist upstream (`logos_independent_lens_latest.json`, etc.)
  3) `eval_multilens_harness_v2_thin.py --populate-default-samples` — `multilens_eval_v2_thin_report_latest.json`
  4) `build_daily_execution_insight_brief_v1.py` — `reports/daily_execution_insight_brief_latest.md`

  Template (human): projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md
#>
param(
    [string]$WorkspaceRoot = 'C:\workspace',
    [switch]$SkipFusionRefresh,
    [switch]$SkipLogosTrackBDeepReport,
    [switch]$SkipThinRefresh,
    [switch]$DatedCopy,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $root

$fusion = @('scripts\report_independent_lens_fusion_stub_v0.py')
$logosDeep = @('scripts\run_logos_track_b_commander_deep_report_v1.py')
$logosMd = @('scripts\materialize_logos_track_b_commander_deep_report_v1.py')
$thinOut = 'docs\final\artifacts\multilens_eval_v2_thin_report_latest.json'
$thin = @(
    'scripts\eval_multilens_harness_v2_thin.py',
    '--populate-default-samples',
    '--out', $thinOut
)
$briefArgs = @('scripts\build_daily_execution_insight_brief_v1.py')
if ($DatedCopy) { $briefArgs += '--also-dated-copy' }

if ($DryRun) {
    if (-not $SkipFusionRefresh) { Write-Host ('py ' + ($fusion -join ' ')) }
    if (-not $SkipLogosTrackBDeepReport) {
        Write-Host ('py ' + ($logosDeep -join ' '))
        Write-Host ('py ' + ($logosMd -join ' '))
    }
    if (-not $SkipThinRefresh) { Write-Host ('py ' + ($thin -join ' ')) }
    Write-Host ('py ' + ($briefArgs -join ' '))
    exit 0
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
    Write-Host '== multilens thin report (populated) ==' -ForegroundColor Cyan
    & py @thin
    if ($LASTEXITCODE -ne 0) { throw "eval_multilens_harness_v2_thin.py failed: $LASTEXITCODE" }
}
Write-Host '== daily execution insight brief ==' -ForegroundColor Cyan
& py @briefArgs
if ($LASTEXITCODE -ne 0) { throw "build_daily_execution_insight_brief_v1.py failed: $LASTEXITCODE" }
Write-Host "OK: brief -> $root\reports\daily_execution_insight_brief_latest.md" -ForegroundColor Green
exit 0
