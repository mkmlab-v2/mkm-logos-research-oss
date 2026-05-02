# B-Track daily chain: independent lenses -> fusion stub -> LLM bundle (S1_SHADOW / observation only).
# Does not call LLM; prepare artifacts for manual or batch LLM step.
# Prerequisites: py on PATH, workspace = C:\workspace (or set $WorkspaceRoot).
#
# Task Scheduler (example, adjust time / user):
#   Program: pwsh.exe
#   Arguments: -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_btrack_daily_hypothesis_chain.ps1"
#   Working directory: C:\workspace
# Recommended registrar:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:40"
# Hit-rate: when research/market_data/kospi_daily_external_yf.csv exists, the chain runs
#   build_btrack_prophecy_score_from_ohlcv.py -> eval_prophecy_hit_rate_v1 --run-mode price
# (B-track [HYPO] only; not live trading). Without CSV, hit-rate eval is skipped with a note.
# Longer window: -IncludeDawnScore (30 trading days for score rows).
# Manual one-offs:
#   py scripts/build_btrack_prophecy_score_from_ohlcv.py
#   py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json docs/final/artifacts/btrack_prophecy_score_latest.json
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [switch]$SkipInsightAppend,
  [switch]$SkipHitRate,
  [switch]$IncludeDawnScore,
  [switch]$SkipExternalFeedValidation,
  [switch]$StrictExternalFeedValidation,
  [switch]$SkipFastPromotionGate,
  [switch]$StrictFastPromotionGate
)
$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if (-not $SkipExternalFeedValidation) {
  $externalLatestRel = "docs\final\artifacts\external_feed_drop_latest.json"
  $externalLatest = Join-Path $WorkspaceRoot $externalLatestRel
  $externalValidatedRel = "docs\final\artifacts\external_feed_drop_latest.validated.json"
  $externalStatusRel = "docs\final\artifacts\external_feed_drop_validation_status_latest.json"
  $externalLoader = Join-Path $WorkspaceRoot "scripts\load_external_feed_drop_with_fallback_v1.py"
  if (Test-Path -LiteralPath $externalLoader) {
    if (Test-Path -LiteralPath $externalLatest) {
      Write-Host "==> external feed validate+fallback (B-track research-only)"
      py $externalLoader --latest $externalLatestRel --output $externalValidatedRel --status-output $externalStatusRel
      if ($LASTEXITCODE -ne 0) {
        if ($StrictExternalFeedValidation) {
          throw "external feed validation failed (strict mode) exit $LASTEXITCODE"
        }
        Write-Host "WARN: external feed validation failed; continue in degraded mode (research-only)." -ForegroundColor Yellow
      }
    } else {
      Write-Host "Skip external feed validate (missing latest drop): $externalLatestRel" -ForegroundColor DarkYellow
    }
  } else {
    Write-Host "Skip external feed validate (missing loader): scripts\load_external_feed_drop_with_fallback_v1.py" -ForegroundColor DarkYellow
  }
}

Write-Host "==> run_lens_myeongni.py"
py scripts/run_lens_myeongni.py
if ($LASTEXITCODE -ne 0) { throw "run_lens_myeongni exit $LASTEXITCODE" }

Write-Host "==> run_lens_sasang.py"
py scripts/run_lens_sasang.py
if ($LASTEXITCODE -ne 0) { throw "run_lens_sasang exit $LASTEXITCODE" }

Write-Host "==> run_market_sasang_lens_v1.py"
py scripts/run_market_sasang_lens_v1.py
if ($LASTEXITCODE -ne 0) { throw "run_market_sasang_lens_v1 exit $LASTEXITCODE" }

Write-Host "==> build_sasang_interpretive_insight_bundle_v1.py (v1.1 interpretive_depth + synthesis_v1; multi-axis reference)"
py scripts/build_sasang_interpretive_insight_bundle_v1.py
if ($LASTEXITCODE -ne 0) { throw "sasang interpretive insight bundle exit $LASTEXITCODE" }

Write-Host "==> run_lens_logos.py"
$logosBatch = Join-Path $WorkspaceRoot "data\logos\4lens_batch_sample.json"
$logosFixture = Join-Path $WorkspaceRoot "tests\fixtures\logos_4lens_batch_minimal_v1.json"
if (Test-Path -LiteralPath $logosBatch) {
  py scripts/run_lens_logos.py --batch-json $logosBatch
} elseif (Test-Path -LiteralPath $logosFixture) {
  Write-Host "Logos: using tracked fixture (data/logos/4lens_batch_sample.json not present)" -ForegroundColor DarkYellow
  py scripts/run_lens_logos.py --batch-json $logosFixture
} else {
  py scripts/run_lens_logos.py --allow-fallback
}
if ($LASTEXITCODE -ne 0) { throw "run_lens_logos exit $LASTEXITCODE" }

Write-Host "==> report_independent_lens_fusion_stub_v0.py"
py scripts/report_independent_lens_fusion_stub_v0.py
if ($LASTEXITCODE -ne 0) { throw "fusion stub exit $LASTEXITCODE" }

Write-Host "==> run_logos_track_b_commander_deep_report_v1.py"
py scripts/run_logos_track_b_commander_deep_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "logos track b commander deep report exit $LASTEXITCODE" }

Write-Host "==> materialize_logos_track_b_commander_deep_report_v1.py"
py scripts/materialize_logos_track_b_commander_deep_report_v1.py
if ($LASTEXITCODE -ne 0) { throw "materialize logos track b commander deep report exit $LASTEXITCODE" }

$minorityMonthly = Join-Path $WorkspaceRoot "scripts\report_independent_lens_shadow_minority_monthly_v1.py"
if (Test-Path -LiteralPath $minorityMonthly) {
  Write-Host "==> report_independent_lens_shadow_minority_monthly_v1.py (shadow JSONL rollup)"
  py $minorityMonthly
  if ($LASTEXITCODE -ne 0) { throw "minority monthly rollup exit $LASTEXITCODE" }
}

Write-Host "==> build_btrack_llm_input_bundle.py"
py scripts/build_btrack_llm_input_bundle.py
if ($LASTEXITCODE -ne 0) { throw "bundle exit $LASTEXITCODE" }

Write-Host "==> generate_btrack_hypothesis_prophecy_v1.py (stub; use --gemini for API)"
py scripts/generate_btrack_hypothesis_prophecy_v1.py
if ($LASTEXITCODE -ne 0) { throw "hypothesis gen exit $LASTEXITCODE" }

if (-not $SkipInsightAppend) {
  $summary = "daily_chain: myeongni+sasang+logos artifacts + fusion stub -> btrack_llm_input_bundle_latest.json"
  $liner = "[HYPO] Independent lens scores fused (observation_only); LLM may read bundle only — not live trading."
  $hook = "If fusion consensus disagrees with forward realized direction over N days, downgrade lens weight in review only."
  py scripts/append_btrack_insight_observation.py `
    --inputs-summary $summary `
    --insight-one-liner $liner `
    --falsification-hook $hook `
    --note "run_btrack_daily_hypothesis_chain.ps1"
  if ($LASTEXITCODE -ne 0) { throw "append insight exit $LASTEXITCODE" }
}

if (-not $SkipHitRate) {
  $kospiCsv = Join-Path $WorkspaceRoot "research\market_data\kospi_daily_external_yf.csv"
  $scoreJsonRel = "docs\final\artifacts\btrack_prophecy_score_latest.json"
  if (Test-Path -LiteralPath $kospiCsv) {
    $btcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
    $buildArgs = @("scripts/build_btrack_prophecy_score_from_ohlcv.py")
    if ($IncludeDawnScore) {
      Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (--recent-trading-days 30) + eval_prophecy_hit_rate_v1 price"
      $buildArgs += @("--recent-trading-days", "30")
    } else {
      Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (default 1d) + eval_prophecy_hit_rate_v1 price"
    }
    if (Test-Path -LiteralPath $btcCsv) {
      $buildArgs += @("--btc-csv", $btcCsv)
    } else {
      Write-Host "WARN: BTC CSV missing; score will be KOSPI-only." -ForegroundColor Yellow
    }
    py @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "build_btrack_prophecy_score exit $LASTEXITCODE" }
    py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreJsonRel
    if ($LASTEXITCODE -ne 0) { throw "eval_prophecy_hit_rate price exit $LASTEXITCODE" }
  } else {
    Write-Host "Skip OHLCV-backed hit rate (missing KOSPI CSV): $kospiCsv" -ForegroundColor Yellow
    Write-Host "==> eval_prophecy_hit_rate_v1.py (proxy; optional registry via env BTRACK_HIT_RATE_REGISTRY_GLOB)"
    $regGlob = [string]$env:BTRACK_HIT_RATE_REGISTRY_GLOB
    if ([string]::IsNullOrWhiteSpace($regGlob)) {
      py scripts/eval_prophecy_hit_rate_v1.py --run-mode proxy
    } else {
      py scripts/eval_prophecy_hit_rate_v1.py --run-mode proxy --registry-glob $regGlob
    }
    if ($LASTEXITCODE -ne 0) { throw "eval_prophecy_hit_rate exit $LASTEXITCODE" }
  }
}

if (-not $SkipFastPromotionGate) {
  Write-Host "==> eval_prophecy_promotion_gates_v1.py (numeric promotion gates)"
  py scripts/eval_prophecy_promotion_gates_v1.py
  if ($LASTEXITCODE -ne 0) {
    if ($StrictFastPromotionGate) {
      throw "eval_prophecy_promotion_gates_v1 exit $LASTEXITCODE"
    }
    Write-Host "WARN: promotion gate eval failed; continue (degraded)." -ForegroundColor Yellow
  }

  Write-Host "==> fast_promotion_gate_v1.py (shadow-fast / live-conditional)"
  py scripts/fast_promotion_gate_v1.py --min-hit-rate 0.5 --min-n 5
  if ($LASTEXITCODE -ne 0) {
    if ($StrictFastPromotionGate) {
      throw "fast_promotion_gate_v1 exit $LASTEXITCODE"
    }
    Write-Host "WARN: fast promotion gate failed; continue (degraded)." -ForegroundColor Yellow
  }
}

Write-Host "OK: B-Track daily hypothesis chain finished. Bundle: docs/final/artifacts/btrack_llm_input_bundle_latest.json"
