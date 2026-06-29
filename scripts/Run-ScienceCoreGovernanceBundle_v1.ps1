<#
.SYNOPSIS
  Science Core governance bundle — horizon, holdout, walk-forward, shock discordant [HYPO][research_only].

.NOTES
  Run from repo root:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-ScienceCoreGovernanceBundle_v1.ps1
#>
[CmdletBinding()]
param(
    [string]$DateFrom = "2026-01-01",
    [string]$DateTo = "2026-06-08",
    [switch]$RebuildScience,
    [switch]$ExtendCalendarStubs,
    [switch]$ExportSidecarHumanist,
    [switch]$RunHumanistAb,
    [switch]$RunLogosAb,
    [switch]$UseMarketSasangPerDate,
    [switch]$UseManseryeokMyeongniPerDate,
    [switch]$UseLogosPerDateMacroGate,
    [switch]$UseFullHumanistPerDate,
    [switch]$RunLongWalkforward,
    [switch]$SkipExtendedAudits,
    [switch]$SkipMacroLongHistory,
    [switch]$RefreshExaNews,
    [switch]$BackfillExaNews,
    [switch]$BackfillExaNewsMonthly2020,
    [switch]$RunNewsWeightAblation,
    [switch]$RunLongWindowLaneCompare,
    [switch]$RunTripleBlendWeightSweep,
    [switch]$RunPnlBootstrap,
    [int]$ExaBackfillStepDays = 7,
    [int]$MacroShuffleTrials = 100
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($UseFullHumanistPerDate) {
    $UseMarketSasangPerDate = $true
    $UseManseryeokMyeongniPerDate = $true
    $UseLogosPerDateMacroGate = $true
}

$exaRefreshOk = $false
if ($BackfillExaNewsMonthly2020) {
    Write-Host "==> backfill_exa_macro_news_observation_v1.py (--preset monthly_2020)" -ForegroundColor Cyan
    py scripts/backfill_exa_macro_news_observation_v1.py `
        --date-to $DateTo `
        --preset monthly_2020 `
        --validate
    if ($LASTEXITCODE -eq 0) {
        $exaRefreshOk = $true
        $RebuildScience = $true
        Write-Host "EXA monthly_2020 backfill OK — full science rebuild enabled." -ForegroundColor DarkGray
    } else {
        Write-Warning "EXA monthly_2020 backfill failed."
    }
}

if ($BackfillExaNews) {
    Write-Host "==> backfill_exa_macro_news_observation_v1.py ($DateFrom .. $DateTo)" -ForegroundColor Cyan
    py scripts/backfill_exa_macro_news_observation_v1.py `
        --date-from $DateFrom `
        --date-to $DateTo `
        --step-days $ExaBackfillStepDays `
        --validate
    if ($LASTEXITCODE -eq 0) {
        $exaRefreshOk = $true
        $RebuildScience = $true
        Write-Host "EXA backfill OK — science per-date rebuild enabled for this run." -ForegroundColor DarkGray
    } else {
        Write-Warning "EXA backfill failed or skipped (EXA_API_KEY?). news_coverage will stay sparse."
    }
}

if ($RefreshExaNews) {
    Write-Host "==> fetch_exa_macro_news_observation_v1.py (--append)" -ForegroundColor Cyan
    py scripts/fetch_exa_macro_news_observation_v1.py --append --validate
    if ($LASTEXITCODE -eq 0) {
        $exaRefreshOk = $true
        $RebuildScience = $true
        Write-Host "EXA ingest OK — science per-date rebuild enabled for this run." -ForegroundColor DarkGray
    } else {
        Write-Warning "EXA news ingest skipped or failed (EXA_API_KEY?). Governance news_coverage will reflect sparse causal rows."
    }
}

if ($ExtendCalendarStubs) {
    Write-Host "==> extend_btrack_calendar_stub_jsonl_v1.py (through $DateTo)" -ForegroundColor Cyan
    py scripts/extend_btrack_calendar_stub_jsonl_v1.py --through-date $DateTo
    if ($LASTEXITCODE -ne 0) { throw "extend calendar stub exit $LASTEXITCODE" }
}

$pyArgs = @(
    "scripts/run_science_core_governance_bundle_v1.py",
    "--date-from", $DateFrom,
    "--date-to", $DateTo
)
if ($RebuildScience) { $pyArgs += "--rebuild-science" }
if ($ExportSidecarHumanist) { $pyArgs += "--export-sidecar-humanist" }
if ($SkipExtendedAudits) { $pyArgs += "--skip-extended-audits" }
if ($SkipMacroLongHistory) { $pyArgs += "--skip-macro-long-history" }
if ($RunHumanistAb) { $pyArgs += "--run-humanist-ab" }
if ($RunNewsWeightAblation) { $pyArgs += "--run-news-weight-ablation" }
if ($RunLongWindowLaneCompare) { $pyArgs += "--run-long-window-lane-compare" }
if ($RunTripleBlendWeightSweep) { $pyArgs += "--run-triple-blend-weight-sweep" }
if ($RunPnlBootstrap) { $pyArgs += "--run-pnl-bootstrap" }
$pyArgs += @("--macro-shuffle-trials", [string]$MacroShuffleTrials)
if ($UseMarketSasangPerDate) {
  py scripts/build_btrack_market_sasang_per_date_jsonl_v1.py --date-from $DateFrom --date-to $DateTo --refresh-market-psych-csv
  if ($LASTEXITCODE -ne 0) { throw "market sasang per-date exit $LASTEXITCODE" }
  $pyArgs += "--use-market-sasang-per-date"
}
if ($UseManseryeokMyeongniPerDate) {
  py scripts/build_btrack_myeongni_per_date_jsonl_v1.py --date-from $DateFrom --date-to $DateTo
  if ($LASTEXITCODE -ne 0) { throw "manseryeok myeongni per-date exit $LASTEXITCODE" }
  $pyArgs += "--use-manseryeok-myeongni-per-date"
}
if ($UseLogosPerDateMacroGate) {
  py scripts/build_btrack_logos_per_date_jsonl_v1.py --date-from $DateFrom --date-to $DateTo
  if ($LASTEXITCODE -ne 0) { throw "logos per-date macro gate exit $LASTEXITCODE" }
  $pyArgs += "--use-logos-per-date-macro-gate"
}
if ($UseMarketSasangPerDate -or $UseManseryeokMyeongniPerDate) {
  $extendArgs = @(
    "scripts/run_science_core_extend_score_sidecar_v1.py",
    "--date-from", $DateFrom,
    "--date-to", $DateTo
  )
  if ($UseMarketSasangPerDate) { $extendArgs += "--rebuild-market-sasang" }
  if ($UseManseryeokMyeongniPerDate) { $extendArgs += "--rebuild-manseryeok-myeongni" }
  if ($UseLogosPerDateMacroGate) { $extendArgs += "--rebuild-logos-per-date" }
  py @extendArgs
  if ($LASTEXITCODE -ne 0) { throw "extend score sidecar exit $LASTEXITCODE" }
}
py @pyArgs
if ($LASTEXITCODE -ne 0) { throw "science core governance bundle exit $LASTEXITCODE" }

if ($RunHumanistAb -and -not $SkipExtendedAudits) {
    Write-Host "==> humanist A/B included in governance bundle (--run-humanist-ab)" -ForegroundColor DarkGray
} elseif ($RunHumanistAb) {
    Write-Host "==> run_science_core_humanist_source_ab_v1.py (standalone; extended audits skipped)" -ForegroundColor Cyan
    $abArgs = @(
        "scripts/run_science_core_humanist_source_ab_v1.py",
        "--date-from", $DateFrom,
        "--date-to", $DateTo
    )
    if ($RebuildScience) { $abArgs += "--rebuild-science" }
    py @abArgs
    if ($LASTEXITCODE -ne 0) { throw "humanist source ab exit $LASTEXITCODE" }
}

if ($RunLogosAb) {
    Write-Host "==> run_science_core_logos_source_ab_v1.py" -ForegroundColor Cyan
    py scripts/run_science_core_logos_source_ab_v1.py --holdout-to $DateTo
    if ($LASTEXITCODE -ne 0) { throw "logos source ab exit $LASTEXITCODE" }
}

if ($RunLongWalkforward) {
    Write-Host "==> run_science_core_long_walkforward_v1.py" -ForegroundColor Cyan
    $lwArgs = @("scripts/run_science_core_long_walkforward_v1.py")
    if ($RebuildScience) { $lwArgs += "--rebuild-science" }
    if ($UseFullHumanistPerDate) { $lwArgs += "--rebuild-per-date" }
    py @lwArgs
    if ($LASTEXITCODE -ne 0) { throw "long walkforward exit $LASTEXITCODE" }
}

Write-Host "OK: science_core_governance_bundle_v1_latest.json" -ForegroundColor Green
