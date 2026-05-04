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
# Market bootstrap (default ON): runs fetch_kospi_yfinance_csv.py + fetch_btc_yfinance_csv.py first
# so stale/missing CSV does not silently force proxy hit-rate mode. Use -SkipMarketDataRefresh for offline/CI.
# News/macro lens JSON: use -SkipNewsMacroAdapter to skip build_btrack_news_macro_lens_adapters_v1.py (reuse prior lens files).
# Hit-rate: when research/market_data/kospi_daily_external_yf.csv exists, the chain runs
#   build_btrack_prophecy_score_from_ohlcv.py -> eval_prophecy_hit_rate_v1 --run-mode price
# BTC dual-leg: --btc-csv when resolved path exists. Resolution order (same idea as Run-BTrackOhlcvScoreAndEval.ps1):
#   1) -BtcCsv parameter  2) env MKM_BTC_DAILY_CSV  3) research/market_data/btc_daily_external_yf.csv
# (B-track [HYPO] only; not live trading). Without CSV, hit-rate eval is skipped with a note.
# Longer window: -IncludeDawnScore (30 trading days for score rows).
# Manual one-offs:
#   py scripts/build_btrack_prophecy_score_from_ohlcv.py
#   py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json docs/final/artifacts/btrack_prophecy_score_latest.json
# Promotion gates: use -PromotionTrackMode dual to evaluate instrument-combo WF + panel-style shared gates (match eval_prophecy_promotion_gates_v1.py).
# Hypothesis LLM: default local ensemble (no API). Use -UseCloudGemini or env MKM_BTRACK_USE_CLOUD_GEMINI=1 for Gemini (--use-cloud-gemini).
# Optional model: -GeminiModel or env MKM_BTRACK_GEMINI_MODEL.
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$BtcCsv = "",
  [ValidateSet("btc_only_crossassist", "dual")]
  [string]$PromotionTrackMode = "btc_only_crossassist",
  [switch]$SkipInsightAppend,
  [switch]$SkipHitRate,
  [switch]$IncludeDawnScore,
  [switch]$SkipExternalFeedValidation,
  [switch]$StrictExternalFeedValidation,
  [switch]$SkipFastPromotionGate,
  [switch]$StrictFastPromotionGate,
  [switch]$SkipMarketDataRefresh,
  [switch]$StrictMarketDataRefresh,
  [switch]$StrictProphecyProxyStreakGate,
  [switch]$UseCloudGemini,
  [string]$GeminiModel = "",
  [switch]$SkipNewsMacroAdapter
)
$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if (-not $SkipMarketDataRefresh) {
  Write-Host "==> fetch_kospi_yfinance_csv.py (market data bootstrap; B-track research-only)"
  py scripts/fetch_kospi_yfinance_csv.py
  if ($LASTEXITCODE -ne 0) {
    if ($StrictMarketDataRefresh) {
      throw "fetch_kospi_yfinance_csv exit $LASTEXITCODE (StrictMarketDataRefresh)"
    }
    Write-Host "WARN: KOSPI CSV fetch failed; chain may fall back to proxy hit-rate if file missing." -ForegroundColor Yellow
  }
  Write-Host "==> fetch_btc_yfinance_csv.py (market data bootstrap; B-track research-only)"
  py scripts/fetch_btc_yfinance_csv.py
  if ($LASTEXITCODE -ne 0) {
    if ($StrictMarketDataRefresh) {
      throw "fetch_btc_yfinance_csv exit $LASTEXITCODE (StrictMarketDataRefresh)"
    }
    Write-Host "WARN: BTC CSV fetch failed; dual-leg score may be KOSPI-only." -ForegroundColor Yellow
  }
} else {
  Write-Host "Skip market data bootstrap (-SkipMarketDataRefresh)." -ForegroundColor DarkYellow
}

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

if (-not $SkipNewsMacroAdapter) {
  Write-Host "==> build_btrack_news_macro_lens_adapters_v1.py (news/macro lens JSON for bundle)"
  py scripts/build_btrack_news_macro_lens_adapters_v1.py
  if ($LASTEXITCODE -ne 0) { throw "build_btrack_news_macro_lens_adapters_v1 exit $LASTEXITCODE" }
} else {
  Write-Host "Skip news/macro lens adapter (-SkipNewsMacroAdapter); bundle uses existing lens JSON paths." -ForegroundColor DarkYellow
}

Write-Host "==> build_btrack_llm_input_bundle.py"
py scripts/build_btrack_llm_input_bundle.py
if ($LASTEXITCODE -ne 0) { throw "bundle exit $LASTEXITCODE" }

$useGemini = [bool]$UseCloudGemini
if (-not $useGemini -and ($env:MKM_BTRACK_USE_CLOUD_GEMINI -eq "1")) {
  $useGemini = $true
}
if ($useGemini) {
  Write-Host "==> generate_btrack_hypothesis_prophecy_v1.py (--use-cloud-gemini; quota/API spend)" -ForegroundColor Cyan
} else {
  Write-Host "==> generate_btrack_hypothesis_prophecy_v1.py (local ensemble default; no Gemini API)"
}
$hypGenArgs = @("scripts/generate_btrack_hypothesis_prophecy_v1.py")
if ($useGemini) {
  $hypGenArgs += "--use-cloud-gemini"
  $gm = [string]$GeminiModel
  if ([string]::IsNullOrWhiteSpace($gm)) {
    $gm = [string]$env:MKM_BTRACK_GEMINI_MODEL
  }
  if (-not [string]::IsNullOrWhiteSpace($gm)) {
    $hypGenArgs += @("--model", $gm.Trim())
  }
}
py @hypGenArgs
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
    $btcDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
    $btcResolved = ""
    if (-not [string]::IsNullOrWhiteSpace($BtcCsv)) {
      if (-not (Test-Path -LiteralPath $BtcCsv)) {
        throw "BtcCsv not found: $BtcCsv"
      }
      $btcResolved = $BtcCsv
    }
    elseif (-not [string]::IsNullOrWhiteSpace($env:MKM_BTC_DAILY_CSV)) {
      $p = [string]$env:MKM_BTC_DAILY_CSV
      if (Test-Path -LiteralPath $p) {
        $btcResolved = $p
      } else {
        Write-Host "WARN: MKM_BTC_DAILY_CSV set but file missing: $p" -ForegroundColor Yellow
      }
    }
    if ([string]::IsNullOrWhiteSpace($btcResolved) -and (Test-Path -LiteralPath $btcDefault)) {
      $btcResolved = $btcDefault
    }
    $buildArgs = @("scripts/build_btrack_prophecy_score_from_ohlcv.py")
    if ($IncludeDawnScore) {
      Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (--recent-trading-days 30) + eval_prophecy_hit_rate_v1 price"
      $buildArgs += @("--recent-trading-days", "30")
    } else {
      Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (default 1d) + eval_prophecy_hit_rate_v1 price"
    }
    if (-not [string]::IsNullOrWhiteSpace($btcResolved)) {
      $buildArgs += @("--btc-csv", $btcResolved)
    } else {
      Write-Host "WARN: BTC CSV missing; score will be KOSPI-only. Set -BtcCsv, MKM_BTC_DAILY_CSV, or add $btcDefault" -ForegroundColor Yellow
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
  Write-Host "==> eval_prophecy_promotion_gates_v1.py (numeric promotion gates, mode=$PromotionTrackMode)"
  py scripts/eval_prophecy_promotion_gates_v1.py --promotion-track-mode $PromotionTrackMode
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

Write-Host "==> build_prophecy_health_status_v1.py (prophecy_health_status_latest.json)"
py scripts/build_prophecy_health_status_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_prophecy_health_status_v1 exit $LASTEXITCODE" }

Write-Host "==> check_prophecy_proxy_streak_gate_v1.py (streak + optional webhook; threshold env MKM_PROPHECY_PROXY_STREAK_THRESHOLD default 3)"
$streakArgs = @("scripts/check_prophecy_proxy_streak_gate_v1.py")
if ($StrictProphecyProxyStreakGate) {
  $streakArgs += "--strict-exit"
}
py @streakArgs
if ($LASTEXITCODE -eq 2) {
  if ($StrictProphecyProxyStreakGate) {
    throw "check_prophecy_proxy_streak_gate_v1: streak breach under strict exit (code 2)"
  }
  Write-Host "WARN: prophecy proxy streak gate reports breach (exit 2). Enable -StrictProphecyProxyStreakGate or MKM_PROPHECY_PROXY_STREAK_STRICT_EXIT=1 to fail the chain." -ForegroundColor Yellow
}
elseif ($LASTEXITCODE -ne 0) {
  throw "check_prophecy_proxy_streak_gate_v1 exit $LASTEXITCODE"
}

Write-Host "OK: B-Track daily hypothesis chain finished. Bundle: docs/final/artifacts/btrack_llm_input_bundle_latest.json"
