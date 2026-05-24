# B-Track daily chain: independent lenses -> fusion stub -> LLM bundle (S1_SHADOW / observation only).
# Does not call LLM; prepare artifacts for manual or batch LLM step.
# Trading policy: BTC-only execution target. KOSPI inputs are observation/info-only.
# Prerequisites: py on PATH, workspace = C:\workspace (or set $WorkspaceRoot).
# Loads `$WorkspaceRoot\.env` into Process env (KEY=value; optional `export `; UTF-8/UTF-16/BOM) before any `py` calls.
#
# Task Scheduler (example, adjust time / user):
#   Program: pwsh.exe
#   Arguments: -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\run_btrack_daily_hypothesis_chain.ps1"
#   Working directory: C:\workspace
# Recommended registrar:
#   powershell -NoProfile -ExecutionPolicy Bypass -File "C:\workspace\scripts\Register-BTrackDailyHypothesisTask.ps1" -At "08:40"
# Panel 24h ALERT 1-3: default runs Check-ProphecyPanel24hAlerts.ps1 at end (writes reports/prophecy_panel_24h_alerts_latest.json,
# appends reports/prophecy_panel_24h_alerts_log.jsonl; failure webhook via .env / User env). Use -SkipPanel24hAlertsCheck to skip.
# Advisory bear-trap (default ON): run_btrack_wrong_dir_holdout_v1.py advisory-sweep before panel (research_only; no ensemble write).
#   Refreshes reports/btrack_advisory_bear_trap_manifest_v1_latest.json from latest per-date directions. Use -SkipAdvisoryBearTrapSweep to skip.
# Model swap PoC harness (default ON): run_btrack_model_swap_harness_v1.py 30d frozen baseline (non-gating; no ensemble write). Use -SkipModelSwapHarness to skip.
# Market bootstrap (default ON): runs fetch_kospi_yfinance_csv.py + fetch_btc_yfinance_csv.py first
# so stale/missing CSV does not silently force proxy hit-rate mode. Use -SkipMarketDataRefresh for offline/CI.
# News/macro lens JSON: use -SkipNewsMacroAdapter to skip build_btrack_news_macro_lens_adapters_v1.py (reuse prior lens files).
# Hit-rate: when research/market_data/kospi_daily_external_yf.csv exists, the chain runs
#   build_btrack_prophecy_score_from_ohlcv.py -> eval_prophecy_hit_rate_v1 --run-mode price
# When BTC CSV resolves, build passes --force-dual-leg-panel (KOSPI∩BTC calendar + both legs per eval_date)
# so instrument_combo walkforward is not skipped as "need at least 2 distinct eval_dates with both kospi+btc legs".
# BTC dual-leg: --btc-csv when resolved path exists. Resolution order (same idea as Run-BTrackOhlcvScoreAndEval.ps1):
#   1) -BtcCsv parameter  2) env MKM_BTC_DAILY_CSV  3) research/market_data/btc_daily_external_yf.csv
# (B-track [HYPO] only; not live trading). Without CSV, hit-rate eval is skipped with a note.
# Phase 3 leading sensors (default OFF): after OHLCV score + price hit-rate eval, optional
#   join_btrack_phase3_leading_sensors_score_v1.py + build_btrack_prophecy_score_insight_sidecar_stub_v1.py
#   (research_only; non-fatal WARN on failure). Use -IncludePhase3LeadingSensors to enable.
#   -SkipPhase3NetworkFetch: skip Binance fetch prefetch (phase3 chain --skip-seed only, no --fetch-binance).
#   -StrictPhase3LeadingSensors or env MKM_BTRACK_PHASE3_LEADING_SENSORS_STRICT=1 fails the chain on hook errors.
# Longer window: -IncludeDawnScore (30 trading days for score rows).
# KOSPI stress observation (default ON): build_kospi_stress_observation_hypothesis_v1.py after prophecy_health_status
# (5d vol + monthly foreign_net_buy proxy; observation_only). Use -SkipKospiStressObservation to omit.
# Manual one-offs:
#   py scripts/build_btrack_prophecy_score_from_ohlcv.py
#   py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json docs/final/artifacts/btrack_prophecy_score_latest.json
# Promotion gates: use -PromotionTrackMode dual to evaluate instrument-combo WF + panel-style shared gates (match eval_prophecy_promotion_gates_v1.py).
# Hypothesis LLM: default local ensemble (no API). Use -UseCloudGemini or env MKM_BTRACK_USE_CLOUD_GEMINI=1 for Gemini (--use-cloud-gemini).
# Optional model: -GeminiModel or env MKM_BTRACK_GEMINI_MODEL.
# Contemplation pilot (BTC research lane): **ON by default** when -ResearchEvaluationInstrument is btc.
# Opt-out only: set MKM_BTRACK_PROPHECY_CONTEMPLATION_V1=0 (or false) to skip run_btrack_prophecy_contemplation_v1.
# multi/kospi lanes never run this gate.
# Optional cost step: MKM_BTRACK_CONTEMPLATION_USE_GEMINI=1 (+ API key) runs a short Gemini JSON reflect after local pass; raise MKM_BTRACK_CONTEMPLATION_TIMEOUT_SEC if needed.
# Force local-only reflect: -SkipProphecyContemplationGemini passes --skip-gemini-reflect to run_btrack_prophecy_contemplation_v1.py (overrides env even when USE_GEMINI=1).
# Naver OpenAPI: default OFF (no network call). Use -IncludeNaverOpenApiRefresh when Client ID/Secret and app APIs are ready. -SkipNaverOpenApiRefresh is legacy no-op unless you need explicit "skip" in wrappers.
# Yang(2015) B-track surface metrics + celebrity benchmark: use -IncludeYang2015SurfaceMetrics (off by default; needs commander JSON for first step).
# Logos insight bundle v1: default runs build_logos_insight_bundle_v1.py after Logos commander materialize (WARN on failure).
#   Skip with -SkipLogosInsightBundle when artifacts are known absent.
# Logos symbolic event promotion chain: use -IncludeLogosSymbolicPromotionChain (research-only; fixture defaults unless explicit JSONL paths provided).
# Logos symbolic fixture fallback: default OFF (operational-safe). Enable only for test/dev.
# Logos blind split + holdout gate: optionally build blind-split news JSONL first, then pass holdout thresholds.
# Logos external feed ingest: optionally convert external_feed_drop_latest.validated.json into non-synthetic
# news_observation_v1 rows before blind split / promotion gate.
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$BtcCsv = "",
  [ValidateSet("btc_only_crossassist", "dual")]
  [string]$PromotionTrackMode = "btc_only_crossassist",
  [switch]$SkipInsightAppend,
  [switch]$SkipHitRate,
  # KPI-B shadow eval (per-date WF on same panel; separate *_kpi_b_shadow_* artifacts only).
  [switch]$SkipKpiBShadowEval,
  # Skip commander-approved KPI-B operational headline promote (shadow-only posture).
  [switch]$SkipKpiBOperationalHeadlinePromote,
  [switch]$IncludeDawnScore,
  [switch]$SkipPerDateDirections,
  [switch]$SkipExternalFeedValidation,
  [switch]$StrictExternalFeedValidation,
  [switch]$SkipFastPromotionGate,
  [switch]$StrictFastPromotionGate,
  [switch]$SkipMarketDataRefresh,
  [switch]$StrictMarketDataRefresh,
  [switch]$StrictProphecyProxyStreakGate,
  [switch]$UseCloudGemini,
  [string]$GeminiModel = "",
  [switch]$IncludeNaverOpenApiRefresh,
  [switch]$SkipNaverOpenApiRefresh,
  [switch]$SkipNewsMacroAdapter,
  [switch]$IncludeYang2015SurfaceMetrics,
  [switch]$IncludeLogosSymbolicPromotionChain,
  [string]$LogosSymbolicNewsJsonl = "",
  [string]$LogosSymbolicLabelsJsonl = "",
  [string]$LogosSymbolicInstrumentId = "KOSPI",
  [string]$LogosSymbolicHorizon = "1d",
  [switch]$AllowLogosSymbolicFixtureFallback,
  [switch]$EnableLogosSymbolicBlindSplit,
  [string]$LogosSymbolicBlindSplitOutJsonl = "docs\final\artifacts\news_observation_v1_blind_split_latest.jsonl",
  [switch]$EnableLogosSymbolicExternalFeedIngest,
  [string]$LogosExternalFeedJson = "docs\final\artifacts\external_feed_drop_latest.validated.json",
  [string]$LogosExternalFeedIngestOutJsonl = "docs\final\artifacts\news_observation_v1_latest.jsonl",
  [int]$LogosMinHoldoutSamples = 10,
  [double]$LogosMinHoldoutHitRate = 0.5,
  [int]$LogosMinNonSyntheticSamples = 10,
  [switch]$EnableLogosSymbolicHumanReviewQueue,
  [string]$LogosSymbolicHumanReviewQueueOutJson = "docs\final\artifacts\logos_symbolic_human_review_queue_latest.json",
  [ValidateSet("btc", "kospi", "multi")]
  [string]$ResearchEvaluationInstrument = "btc",
  [switch]$SkipProphecyContemplationGemini,
  [switch]$SkipPanel24hAlertsCheck,
  [switch]$SkipAdvisoryBearTrapSweep,
  [switch]$SkipModelSwapHarness,
  [double]$Panel24hMinHitRate = 0.60,
  [switch]$SkipKospiStressObservation,
  # Ensemble v2 recommended eval (strict 0.55 gates); also MKM_BTRACK_ENSEMBLE_V2_DAILY=1 in .env.
  [switch]$IncludeEnsembleV2RecommendedEval,
  # Logos B-track observational bundle (upstream JSON/JSONL may be absent; non-blocking WARN).
  [switch]$SkipLogosInsightBundle,
  # Phase 3 leading-sensor join + insight sidecar after price hit-rate (research_only; default OFF).
  [switch]$IncludePhase3LeadingSensors,
  [switch]$SkipPhase3NetworkFetch,
  [switch]$StrictPhase3LeadingSensors,
  # Sasang pathology ↔ TE sandbox mapping (default ON; research_only; weight_hint=0).
  [switch]$SkipPathologyTeMapping,
  # Walk-forward folds for daily shadow refresh (align with run_btrack_promotion_push_v1 default 6).
  [int]$ProphecyWalkforwardNFolds = 6
)
$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

# Load workspace .env into Process scope so child `py` invocations see API keys (Naver, etc.).
# Line contract: KEY=value, optional "export ", optional quotes on value; UTF-8 / UTF-16 LE / BOM-safe; no value logging.
$dotEnv = Join-Path $WorkspaceRoot ".env"
if (Test-Path -LiteralPath $dotEnv) {
    $bytes = [System.IO.File]::ReadAllBytes($dotEnv)
    $text = $null
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $utf8 = New-Object System.Text.UTF8Encoding $false
        $text = $utf8.GetString($bytes, 3, $bytes.Length - 3)
    }
    elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
        $text = [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
    }
    elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
        $text = [System.Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
    }
    else {
        $utf8 = New-Object System.Text.UTF8Encoding $false
        $text = $utf8.GetString($bytes)
    }
    foreach ($rawLine in $text -split "`r?`n") {
        $line = $rawLine.Trim().TrimStart([char]0xFEFF)
        if (-not $line -or $line.StartsWith("#")) { continue }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { continue }
        $key = $line.Substring(0, $eq).Trim().TrimStart([char]0xFEFF)
        $val = $line.Substring($eq + 1).Trim()
        if ($key.StartsWith("export ", [System.StringComparison]::OrdinalIgnoreCase)) {
            $key = $key.Substring(7).Trim()
        }
        if ($val.Length -ge 2 -and (
                ($val.StartsWith([char]34) -and $val.EndsWith([char]34)) -or
                ($val.StartsWith([char]39) -and $val.EndsWith([char]39)))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        if (-not $key) { continue }
        [Environment]::SetEnvironmentVariable($key, $val, "Process")
    }
    if ($IncludeNaverOpenApiRefresh -and
        -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("NAVER_CLIENT_ID", "Process")) -and
        -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("NAVER_CLIENT_SECRET", "Process"))) {
        Write-Host "Dotenv: NAVER_CLIENT_ID + NAVER_CLIENT_SECRET loaded into process (values not logged)." -ForegroundColor DarkGray
    }
}

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

$doNaverOpenApiRefresh = $false
if ($IncludeNaverOpenApiRefresh -and -not $SkipNaverOpenApiRefresh) {
  $doNaverOpenApiRefresh = $true
}
if (-not $doNaverOpenApiRefresh) {
  Write-Host "Skip Naver OpenAPI refresh (default; use -IncludeNaverOpenApiRefresh when ready)." -ForegroundColor DarkYellow
} else {
  $naverScript = Join-Path $WorkspaceRoot "scripts\fetch_naver_openapi_signals_v1.py"
  if (Test-Path -LiteralPath $naverScript) {
    if ([string]::IsNullOrWhiteSpace($env:NAVER_CLIENT_ID) -or [string]::IsNullOrWhiteSpace($env:NAVER_CLIENT_SECRET)) {
      Write-Host "Skip Naver OpenAPI refresh (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET missing after .env load)." -ForegroundColor DarkYellow
    } else {
      Write-Host "==> fetch_naver_openapi_signals_v1.py (research-only Naver trend/news ingest)"
      $naverArgs = @($naverScript, "--allow-cache-fallback")
      if (-not [string]::IsNullOrWhiteSpace($env:MKM_NAVER_NEWS_QUERY)) {
        $naverArgs += @("--news-query", [string]$env:MKM_NAVER_NEWS_QUERY)
      }
      if (-not [string]::IsNullOrWhiteSpace($env:MKM_NAVER_TREND_KEYWORDS)) {
        $naverArgs += @("--trend-keywords", [string]$env:MKM_NAVER_TREND_KEYWORDS)
      }
      if (-not [string]::IsNullOrWhiteSpace($env:MKM_NAVER_TREND_WEIGHTS)) {
        $naverArgs += @("--trend-weights", [string]$env:MKM_NAVER_TREND_WEIGHTS)
      }
      py @naverArgs
      if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: Naver OpenAPI refresh failed; continue with existing artifacts." -ForegroundColor Yellow
      }
    }
  }
}

$externalSignalsScript = Join-Path $WorkspaceRoot "scripts\fetch_external_macro_news_signals_v1.py"
if (Test-Path -LiteralPath $externalSignalsScript) {
  if ([string]::IsNullOrWhiteSpace($env:FRED_API_KEY) -and [string]::IsNullOrWhiteSpace($env:NEWSAPI_API_KEY)) {
    Write-Host "Skip external macro/news refresh (FRED_API_KEY and NEWSAPI_API_KEY missing)." -ForegroundColor DarkYellow
  } else {
    Write-Host "==> fetch_external_macro_news_signals_v1.py (research-only external macro/news ingest)"
    py $externalSignalsScript --allow-cache-fallback
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: external macro/news refresh failed; continue with existing artifacts." -ForegroundColor Yellow
    }
  }
}

$btcSignalsScript = Join-Path $WorkspaceRoot "scripts\fetch_btc_market_signals_v1.py"
if (Test-Path -LiteralPath $btcSignalsScript) {
  Write-Host "==> fetch_btc_market_signals_v1.py (research-only BTC market micro ingest)"
  py $btcSignalsScript
  if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: BTC market signal refresh failed; continue with existing artifacts." -ForegroundColor Yellow
  }
}

$btcAltPublicScript = Join-Path $WorkspaceRoot "scripts\fetch_btc_alt_public_signals_v1.py"
if (Test-Path -LiteralPath $btcAltPublicScript) {
  Write-Host "==> fetch_btc_alt_public_signals_v1.py (research-only BTC alt public ingest)"
  py $btcAltPublicScript
  if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: BTC alt public signal refresh failed; continue with existing artifacts." -ForegroundColor Yellow
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

if (-not $SkipLogosInsightBundle) {
  Write-Host "==> build_logos_insight_bundle_v1.py (Logos upstream digest; best-effort if Aramaic/morphology artifacts missing)"
  py scripts/build_logos_insight_bundle_v1.py
  if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: build_logos_insight_bundle_v1 failed; chain continues." -ForegroundColor Yellow
  }
}

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

if (-not $SkipPathologyTeMapping) {
  Write-Host "==> dump_unified_trading_monitor_te_snapshot_v1.py (monitoring_latest.json TE probe)"
  py scripts/dump_unified_trading_monitor_te_snapshot_v1.py
  if ($LASTEXITCODE -ne 0) { throw "dump_unified_trading_monitor_te_snapshot_v1 exit $LASTEXITCODE" }
  Write-Host "==> export_btrack_transfer_entropy_snapshot_v1.py (B-track TE snapshot / detector)"
  py scripts/export_btrack_transfer_entropy_snapshot_v1.py
  if ($LASTEXITCODE -ne 0) { throw "export_btrack_transfer_entropy_snapshot_v1 exit $LASTEXITCODE" }
  Write-Host "==> build_sasang_pathology_te_mapping_hypo_v1.py ([HYPO] pathology↔TE band; weight_hint=0)"
  py scripts/build_sasang_pathology_te_mapping_hypo_v1.py
  if ($LASTEXITCODE -ne 0) { throw "build_sasang_pathology_te_mapping_hypo_v1 exit $LASTEXITCODE" }
  Write-Host "==> build_compression_prophecy_bridge_status_v1.py (compression + interpretive audit)"
  py scripts/build_compression_prophecy_bridge_status_v1.py
  if ($LASTEXITCODE -ne 0) { throw "build_compression_prophecy_bridge_status_v1 exit $LASTEXITCODE" }
} else {
  Write-Host "Skip pathology TE mapping (-SkipPathologyTeMapping)." -ForegroundColor DarkYellow
}

$contemplationJsonArg = $null
$contemplationEnv = [string]$env:MKM_BTRACK_PROPHECY_CONTEMPLATION_V1
$contemplationOptOut = ($contemplationEnv -eq "0" -or $contemplationEnv -ieq "false")
$contemplationOn = ($ResearchEvaluationInstrument -eq "btc") -and (-not $contemplationOptOut)
if ($contemplationOn) {
  Write-Host "==> run_btrack_prophecy_contemplation_v1.py (BTC lane pre-gate; opt-out: MKM_BTRACK_PROPHECY_CONTEMPLATION_V1=0)" -ForegroundColor Cyan
  $contemplPyArgs = @("scripts/run_btrack_prophecy_contemplation_v1.py")
  if ($SkipProphecyContemplationGemini) {
    $contemplPyArgs += "--skip-gemini-reflect"
    Write-Host "  (Gemini reflect skipped: -SkipProphecyContemplationGemini)" -ForegroundColor DarkYellow
  }
  py @contemplPyArgs
  if ($LASTEXITCODE -ne 0) { throw "run_btrack_prophecy_contemplation_v1 exit $LASTEXITCODE" }
  $contemplationJsonArg = "docs/final/artifacts/btrack_prophecy_contemplation_v1_latest.json"
}

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
if ($ResearchEvaluationInstrument -ne "btc") {
  $hypGenArgs += @("--research-evaluation-instrument", $ResearchEvaluationInstrument)
}
if ($null -ne $contemplationJsonArg) {
  $hypGenArgs += @("--contemplation-json", $contemplationJsonArg)
}
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
  $kpiBApprovalPath = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_dual_kpi_headline_human_approval_v1_latest.json"
  $kpiBApproved = $false
  if (Test-Path -LiteralPath $kpiBApprovalPath) {
    try {
      $kpiBAp = Get-Content -LiteralPath $kpiBApprovalPath -Raw -Encoding UTF8 | ConvertFrom-Json
      $kpiBApproved = ([string]$kpiBAp.decision -eq "APPROVED_KPI_B_OPERATIONAL_HEADLINE")
    } catch {
      Write-Host "WARN: could not read KPI-B approval JSON: $kpiBApprovalPath" -ForegroundColor Yellow
    }
  }
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
    $perDateDirsRel = "reports\btrack_ensemble_per_date_directions_v1_latest.json"
    if ($kpiBApproved -and -not $SkipKpiBOperationalHeadlinePromote -and -not [string]::IsNullOrWhiteSpace($btcResolved)) {
      Write-Host "==> KPI-B operational headline (commander approved): run_btrack_kpi_b_shadow_eval_v1.py --promote-to-operational-headline" -ForegroundColor Cyan
      $kpiAArchiveRel = "docs\final\artifacts\prophecy_hit_rate_eval_kpi_a_frozen_archive_v1_latest.json"
      $shadowArgs = @(
        "scripts/run_btrack_kpi_b_shadow_eval_v1.py",
        "--btc-csv", $btcResolved,
        "--promote-to-operational-headline"
      )
      if (Test-Path -LiteralPath (Join-Path $WorkspaceRoot $kpiAArchiveRel)) {
        $shadowArgs += @("--kpi-a-eval-json", $kpiAArchiveRel)
      }
      py @shadowArgs
      if ($LASTEXITCODE -ne 0) { throw "run_btrack_kpi_b_shadow_eval promote exit $LASTEXITCODE" }
    }
    else {
    if ($IncludeDawnScore -and -not $SkipPerDateDirections -and -not [string]::IsNullOrWhiteSpace($btcResolved)) {
      Write-Host "==> build_btrack_ensemble_per_date_directions_v1.py (--recent-trading-days 30, target=btc)"
      py scripts/build_btrack_ensemble_per_date_directions_v1.py --recent-trading-days 30 --target-instrument btc
      if ($LASTEXITCODE -ne 0) { throw "build_btrack_ensemble_per_date_directions_v1 exit $LASTEXITCODE" }
    }
    $buildArgs = @("scripts/build_btrack_prophecy_score_from_ohlcv.py")
    if ($IncludeDawnScore) {
      Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (--recent-trading-days 30, per-date dirs when enabled, dual-leg panel) + eval"
      $buildArgs += @("--recent-trading-days", "30")
    } else {
      Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py (default 1d, --force-dual-leg-panel when BTC CSV) + eval_prophecy_hit_rate_v1 price"
    }
    if (-not [string]::IsNullOrWhiteSpace($btcResolved)) {
      $buildArgs += @("--btc-csv", $btcResolved)
      $buildArgs += "--force-dual-leg-panel"
      if ($IncludeDawnScore -and -not $SkipPerDateDirections) {
        $perDateDirsPath = Join-Path $WorkspaceRoot $perDateDirsRel
        if (Test-Path -LiteralPath $perDateDirsPath) {
          $buildArgs += @("--per-date-direction-json", $perDateDirsRel)
        } else {
          Write-Host "WARN: per-date directions missing; score uses frozen hypothesis only: $perDateDirsPath" -ForegroundColor Yellow
        }
      }
    } else {
      Write-Host "WARN: BTC CSV missing; score will be KOSPI-only. Set -BtcCsv, MKM_BTC_DAILY_CSV, or add $btcDefault" -ForegroundColor Yellow
    }
    py @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "build_btrack_prophecy_score exit $LASTEXITCODE" }
    py scripts/eval_prophecy_hit_rate_v1.py --run-mode price --score-json $scoreJsonRel
    if ($LASTEXITCODE -ne 0) { throw "eval_prophecy_hit_rate price exit $LASTEXITCODE" }
    if ($IncludePhase3LeadingSensors) {
      $scorePathAbs = Join-Path $WorkspaceRoot $scoreJsonRel
      $strictPhase3Leading = $StrictPhase3LeadingSensors
      if (-not $strictPhase3Leading) {
        $p3StrictEnv = [string]$env:MKM_BTRACK_PHASE3_LEADING_SENSORS_STRICT
        $strictPhase3Leading = $p3StrictEnv.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
      }
      if (-not (Test-Path -LiteralPath $scorePathAbs)) {
        $msg = "IncludePhase3LeadingSensors: score file missing: $scorePathAbs"
        if ($strictPhase3Leading) { throw $msg }
        Write-Host "WARN: $msg" -ForegroundColor Yellow
      } else {
        if (-not $SkipPhase3NetworkFetch) {
          Write-Host "==> run_btrack_phase3_leading_sensors_chain_v1.py (--skip-seed --fetch-binance; skip join/sidecar prefetch)"
          $phase3ChainArgs = @(
            "scripts/run_btrack_phase3_leading_sensors_chain_v1.py",
            "--skip-seed",
            "--fetch-binance",
            "--skip-auto-optimal",
            "--skip-join",
            "--skip-sidecar-refresh"
          )
          py @phase3ChainArgs
          if ($LASTEXITCODE -ne 0) {
            if ($strictPhase3Leading) { throw "run_btrack_phase3_leading_sensors_chain exit $LASTEXITCODE" }
            Write-Host "WARN: Phase3 leading-sensors chain exit $LASTEXITCODE; continuing to join." -ForegroundColor Yellow
          }
        } else {
          Write-Host "==> Phase3 network fetch skipped (-SkipPhase3NetworkFetch); join uses existing sensor stubs"
        }
        Write-Host "==> join_btrack_phase3_leading_sensors_score_v1.py (--instrument btc; research_only)"
        py scripts/join_btrack_phase3_leading_sensors_score_v1.py --score-json $scoreJsonRel --instrument btc
        if ($LASTEXITCODE -ne 0) {
          if ($strictPhase3Leading) { throw "join_btrack_phase3_leading_sensors_score exit $LASTEXITCODE" }
          Write-Host "WARN: join_btrack_phase3_leading_sensors_score exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
        }
        Write-Host "==> build_btrack_prophecy_score_insight_sidecar_stub_v1.py (research_only)"
        py scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py
        if ($LASTEXITCODE -ne 0) {
          if ($strictPhase3Leading) { throw "build_btrack_prophecy_score_insight_sidecar_stub exit $LASTEXITCODE" }
          Write-Host "WARN: build_btrack_prophecy_score_insight_sidecar_stub exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
        }
      }
    }
    if (-not $SkipKpiBShadowEval -and -not [string]::IsNullOrWhiteSpace($btcResolved)) {
      Write-Host "==> run_btrack_kpi_b_shadow_eval_v1.py (KPI-B shadow; prod headline unchanged)" -ForegroundColor Cyan
      py scripts/run_btrack_kpi_b_shadow_eval_v1.py --score-json $scoreJsonRel --btc-csv $btcResolved
      if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: KPI-B shadow eval exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
      }
    }
    }
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
  Write-Host "==> run_prophecy_per_date_combo_walkforward_v1.py (refresh per-date WF on latest score; n-folds=$ProphecyWalkforwardNFolds)"
  py scripts/run_prophecy_per_date_combo_walkforward_v1.py --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" --n-folds $ProphecyWalkforwardNFolds
  if ($LASTEXITCODE -ne 0) {
    if ($StrictFastPromotionGate) {
      throw "run_prophecy_per_date_combo_walkforward_v1 exit $LASTEXITCODE"
    }
    Write-Host "WARN: per-date walkforward refresh failed; promotion gate may use stale artifact." -ForegroundColor Yellow
  }

  Write-Host "==> run_prophecy_instrument_combo_walkforward_v1.py (refresh instrument WF; n-folds=$ProphecyWalkforwardNFolds inject-sweep-best)"
  py scripts/run_prophecy_instrument_combo_walkforward_v1.py --score-json "docs/final/artifacts/btrack_prophecy_score_latest.json" --n-folds $ProphecyWalkforwardNFolds --inject-sweep-best --selection-mode inner-cv --inner-folds 3 --train-objective beat_bull_first
  if ($LASTEXITCODE -ne 0) {
    if ($StrictFastPromotionGate) {
      throw "run_prophecy_instrument_combo_walkforward_v1 exit $LASTEXITCODE"
    }
    Write-Host "WARN: instrument walkforward refresh failed; promotion gate may use stale artifact." -ForegroundColor Yellow
  }

  Write-Host "==> eval_prophecy_promotion_gates_v1.py (numeric promotion gates, mode=$PromotionTrackMode -> daily shadow only)"
  # Strict SSOT (docs/final/artifacts/prophecy_promotion_gates_v1_latest.json) is written only by
  # recommended/dual-strict/promotion-bundle chains — never by this daily shadow path.
  py scripts/eval_prophecy_promotion_gates_v1.py --promotion-track-mode $PromotionTrackMode --output docs/final/artifacts/prophecy_promotion_gates_daily_shadow_v1_latest.json
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

$ensembleV2On = [bool]$IncludeEnsembleV2RecommendedEval
if (-not $ensembleV2On) {
  $ensEnv = [string]$env:MKM_BTRACK_ENSEMBLE_V2_DAILY
  $ensembleV2On = ($ensEnv -eq "1" -or $ensEnv -ieq "true" -or $ensEnv -ieq "yes" -or $ensEnv -ieq "on")
}
if ($ensembleV2On) {
  Write-Host "==> run_prophecy_btrack_recommended_eval_chain_v1.py (--ensemble-v2-lane; B-track risk SSOT, not Aroon orders)" -ForegroundColor Cyan
  py scripts/run_prophecy_btrack_recommended_eval_chain_v1.py --ensemble-v2-lane --neutral-bps 0.8
  if ($LASTEXITCODE -ne 0) { throw "ensemble v2 recommended eval exit $LASTEXITCODE" }
  py scripts/refresh_gut_brain_btrack_promotion_status_v1.py
  if ($LASTEXITCODE -ne 0) { throw "refresh_gut_brain_btrack_promotion_status_v1 exit $LASTEXITCODE" }
}

Write-Host "==> build_btrack_daily_p15_shadow_status_v1.py (P1.5 abstain shadow tag; observation_only)"
py scripts/build_btrack_daily_p15_shadow_status_v1.py
if ($LASTEXITCODE -ne 0) {
  Write-Host "WARN: build_btrack_daily_p15_shadow_status_v1 exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
}

Write-Host "==> build_prophecy_health_status_v1.py (prophecy_health_status_latest.json)"
py scripts/build_prophecy_health_status_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_prophecy_health_status_v1 exit $LASTEXITCODE" }

if (-not $SkipKospiStressObservation) {
  Write-Host "==> build_kospi_stress_observation_hypothesis_v1.py (B-track [HYPO] KOSPI vol + monthly flow proxy; observation_only)"
  py scripts/build_kospi_stress_observation_hypothesis_v1.py --append-log
  if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: build_kospi_stress_observation_hypothesis_v1 exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
  }
}

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

if ($IncludeYang2015SurfaceMetrics) {
  $cmdJson = Join-Path $WorkspaceRoot "reports\commander_myeongni_lens_latest.json"
  $yangOut = Join-Path $WorkspaceRoot "reports\btrack_yang_2015_style_metrics_latest.json"
  if (Test-Path -LiteralPath $cmdJson) {
    Write-Host "==> btrack_yang_2015_style_metrics_v1.py (Yang 2015 surface metrics; B-track)" -ForegroundColor Cyan
    py scripts/btrack_yang_2015_style_metrics_v1.py --input $cmdJson --out $yangOut
    if ($LASTEXITCODE -ne 0) { throw "btrack_yang_2015_style_metrics_v1 exit $LASTEXITCODE" }
  } else {
    Write-Host "WARN: Skip Yang surface metrics step: missing commander JSON ($cmdJson)" -ForegroundColor Yellow
  }
  $benchOut = Join-Path $WorkspaceRoot "docs\final\artifacts\myeongni_celebrity_hit_rate_v1.json"
  Write-Host "==> run_myeongni_celebrity_benchmark_v1.py (fixture bench + v2 + yang_2015_style_metrics)" -ForegroundColor Cyan
  py scripts/run_myeongni_celebrity_benchmark_v1.py --out $benchOut
  if ($LASTEXITCODE -ne 0) { throw "run_myeongni_celebrity_benchmark_v1 exit $LASTEXITCODE" }
}

if ($IncludeLogosSymbolicPromotionChain) {
  $logosChainScript = Join-Path $WorkspaceRoot "scripts\run_logos_symbolic_promotion_chain_v1.py"
  if (-not (Test-Path -LiteralPath $logosChainScript)) {
    throw "Missing logos symbolic promotion chain script: $logosChainScript"
  }
  if ($EnableLogosSymbolicExternalFeedIngest) {
    $externalIngestScript = Join-Path $WorkspaceRoot "scripts\build_news_observation_from_external_feed_v1.py"
    if (-not (Test-Path -LiteralPath $externalIngestScript)) {
      throw "Missing external feed ingest script: $externalIngestScript"
    }
    Write-Host "==> build_news_observation_from_external_feed_v1.py (Logos non-synthetic ingest)"
    py $externalIngestScript `
      --external-feed-json $LogosExternalFeedJson `
      --append-existing-jsonl $LogosExternalFeedIngestOutJsonl `
      --output-jsonl $LogosExternalFeedIngestOutJsonl `
      --validate
    if ($LASTEXITCODE -ne 0) { throw "build_news_observation_from_external_feed_v1 exit $LASTEXITCODE" }
    if ([string]::IsNullOrWhiteSpace($LogosSymbolicNewsJsonl)) {
      $LogosSymbolicNewsJsonl = $LogosExternalFeedIngestOutJsonl
    }
  }

  if ($EnableLogosSymbolicBlindSplit) {
    $blindSplitScript = Join-Path $WorkspaceRoot "scripts\build_news_observation_blind_split_v1.py"
    if (-not (Test-Path -LiteralPath $blindSplitScript)) {
      throw "Missing blind split script: $blindSplitScript"
    }
    $blindIn = $null
    if (-not [string]::IsNullOrWhiteSpace($LogosSymbolicNewsJsonl)) {
      if (-not (Test-Path -LiteralPath $LogosSymbolicNewsJsonl)) {
        throw "LogosSymbolicNewsJsonl not found for blind split: $LogosSymbolicNewsJsonl"
      }
      $blindIn = $LogosSymbolicNewsJsonl
    } else {
      $blindIn = "docs\final\artifacts\news_observation_v1_latest.jsonl"
      $blindInAbs = Join-Path $WorkspaceRoot $blindIn
      if (-not (Test-Path -LiteralPath $blindInAbs)) {
        throw "Blind split source missing: $blindInAbs"
      }
    }
    Write-Host "==> build_news_observation_blind_split_v1.py (Logos symbolic blind split)"
    py $blindSplitScript --input-jsonl $blindIn --output-jsonl $LogosSymbolicBlindSplitOutJsonl --train-pct 70 --calibration-pct 15
    if ($LASTEXITCODE -ne 0) { throw "build_news_observation_blind_split_v1 exit $LASTEXITCODE" }
    $LogosSymbolicNewsJsonl = $LogosSymbolicBlindSplitOutJsonl
  }
  Write-Host "==> run_logos_symbolic_promotion_chain_v1.py (B-track symbolic backtest + promotion gate)"
  $logosArgs = @(
    $logosChainScript,
    "--instrument-id",
    $LogosSymbolicInstrumentId,
    "--horizon",
    $LogosSymbolicHorizon,
    "--min-holdout-samples",
    "$LogosMinHoldoutSamples",
    "--min-holdout-hit-rate",
    "$LogosMinHoldoutHitRate",
    "--min-non-synthetic-samples",
    "$LogosMinNonSyntheticSamples"
  )
  if ($AllowLogosSymbolicFixtureFallback) {
    Write-Host "WARN: Allowing Logos symbolic fixture fallback (test/dev mode)." -ForegroundColor Yellow
    $logosArgs += "--allow-fixture-fallback"
  }
  if (-not [string]::IsNullOrWhiteSpace($LogosSymbolicNewsJsonl)) {
    if (-not (Test-Path -LiteralPath $LogosSymbolicNewsJsonl)) {
      throw "LogosSymbolicNewsJsonl not found: $LogosSymbolicNewsJsonl"
    }
    $logosArgs += @("--news-jsonl", $LogosSymbolicNewsJsonl)
  }
  if (-not [string]::IsNullOrWhiteSpace($LogosSymbolicLabelsJsonl)) {
    if (-not (Test-Path -LiteralPath $LogosSymbolicLabelsJsonl)) {
      throw "LogosSymbolicLabelsJsonl not found: $LogosSymbolicLabelsJsonl"
    }
    $logosArgs += @("--labels-jsonl", $LogosSymbolicLabelsJsonl)
  }
  py @logosArgs
  if ($LASTEXITCODE -ne 0) { throw "run_logos_symbolic_promotion_chain_v1 exit $LASTEXITCODE" }

  if ($EnableLogosSymbolicHumanReviewQueue) {
    $queueScript = Join-Path $WorkspaceRoot "scripts\build_logos_symbolic_human_review_queue_v1.py"
    if (-not (Test-Path -LiteralPath $queueScript)) {
      throw "Missing queue builder script: $queueScript"
    }
    Write-Host "==> build_logos_symbolic_human_review_queue_v1.py (queue only; no auto approval)"
    py $queueScript `
      --promotion-gate-json "docs\final\artifacts\logos_symbolic_event_promotion_gate_latest.json" `
      --output-json $LogosSymbolicHumanReviewQueueOutJson
    if ($LASTEXITCODE -ne 0) { throw "build_logos_symbolic_human_review_queue_v1 exit $LASTEXITCODE" }
  }
}

if (-not $SkipAdvisoryBearTrapSweep) {
  $perDateDirsPath = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_v1_latest.json"
  $btcDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
  if (-not (Test-Path -LiteralPath $perDateDirsPath) -and (Test-Path -LiteralPath $btcDefault)) {
    Write-Host "==> build_btrack_ensemble_per_date_directions_v1.py (advisory prereq; 30d btc)" -ForegroundColor Cyan
    py scripts/build_btrack_ensemble_per_date_directions_v1.py --recent-trading-days 30 --target-instrument btc
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: per-date directions build failed; skip advisory-sweep (exit $LASTEXITCODE)." -ForegroundColor Yellow
    }
  }
  if (Test-Path -LiteralPath $perDateDirsPath) {
    Write-Host "==> run_btrack_wrong_dir_holdout_v1.py advisory-sweep (primary advisory_ovn_bull; direction unchanged)" -ForegroundColor Cyan
    py scripts/run_btrack_wrong_dir_holdout_v1.py advisory-sweep
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: advisory-sweep exit $LASTEXITCODE; continuing chain (non-gating)." -ForegroundColor Yellow
    }
    Write-Host "==> build_btrack_holdout_gate_candidate_manifest_v1.py (holdout_ovn_signed_bull; research_only)" -ForegroundColor Cyan
    py scripts/build_btrack_holdout_gate_candidate_manifest_v1.py --skip-probe-refresh
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: holdout gate candidate manifest exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
    }
    Write-Host "==> build_btrack_holdout_gate_oos_180d_eval_v1.py (holdout gate 180d OOS; research_only)" -ForegroundColor Cyan
    py scripts/build_btrack_holdout_gate_oos_180d_eval_v1.py
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: holdout gate OOS 180d exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
    }
    Write-Host "==> build_btrack_holdout_price_lens_cf_holdout7_v1.py (CF vs gate; research_only)" -ForegroundColor Cyan
    py scripts/build_btrack_holdout_price_lens_cf_holdout7_v1.py
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: holdout price-lens CF summary exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
    }
    Write-Host "==> build_btrack_holdout7_gate_research_pack_v1.py (holdout7 gate pack refresh)" -ForegroundColor Cyan
    py scripts/build_btrack_holdout7_gate_research_pack_v1.py
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: holdout7 gate research pack exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
    }
    Write-Host "==> build_btrack_train_wrong_pattern_summary_v1.py (180d train_wrong vs holdout7)" -ForegroundColor Cyan
    py scripts/build_btrack_train_wrong_pattern_summary_v1.py
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: train_wrong pattern summary exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
    }
    if ((Test-Path -LiteralPath (Join-Path $WorkspaceRoot "reports\btrack_wrong_dir_holdout_features_180d_v1_latest.json")) -and
        (Test-Path -LiteralPath (Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_180d_v1_latest.json"))) {
      Write-Host "==> run_btrack_wrong_dir_holdout_v1.py eval-grid-180 (aux sweep incl. holdout_ovn_signed_bull)" -ForegroundColor Cyan
      py scripts/run_btrack_wrong_dir_holdout_v1.py eval-grid-180
      if ($LASTEXITCODE -ne 0) {
        Write-Host "WARN: eval-grid-180 exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
      }
    }
    Write-Host "==> build_btrack_prophecy_observation_mode_status_v1.py (ops freeze snapshot)" -ForegroundColor Cyan
    py scripts/build_btrack_prophecy_observation_mode_status_v1.py
    if ($LASTEXITCODE -ne 0) {
      Write-Host "WARN: observation mode status exit $LASTEXITCODE; continuing." -ForegroundColor Yellow
    }
  } else {
    Write-Host "WARN: Skip advisory-sweep (missing per-date directions): $perDateDirsPath" -ForegroundColor Yellow
  }
} else {
  Write-Host "Skip advisory bear-trap sweep (-SkipAdvisoryBearTrapSweep)." -ForegroundColor DarkYellow
}

if (-not $SkipModelSwapHarness) {
  Write-Host "==> run_btrack_model_swap_harness_v1.py (30d frozen baseline; research_only)" -ForegroundColor Cyan
  py scripts/run_btrack_model_swap_harness_v1.py
  if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: model swap harness exit $LASTEXITCODE; continuing chain (non-gating)." -ForegroundColor Yellow
  }
} else {
  Write-Host "Skip model swap harness (-SkipModelSwapHarness)." -ForegroundColor DarkYellow
}

if (-not $SkipPanel24hAlertsCheck) {
  $panelScript = Join-Path $WorkspaceRoot "scripts\Check-ProphecyPanel24hAlerts.ps1"
  if (Test-Path -LiteralPath $panelScript) {
    Write-Host "==> Check-ProphecyPanel24hAlerts.ps1 (panel 24h ALERT 1-3; SSOT + optional webhook on failure)" -ForegroundColor Cyan
    $panelOutJson = Join-Path $WorkspaceRoot "reports\prophecy_panel_24h_alerts_latest.json"
    & $panelScript -WorkspaceRoot $WorkspaceRoot -MinHitRate $Panel24hMinHitRate -OutJson $panelOutJson -AppendLog
    if ($LASTEXITCODE -ne 0) {
      throw "Check-ProphecyPanel24hAlerts exit $LASTEXITCODE"
    }
  } else {
    Write-Host "WARN: Skip panel 24h check (missing script): $panelScript" -ForegroundColor Yellow
  }
} else {
  Write-Host "Skip panel 24h alerts check (-SkipPanel24hAlertsCheck)." -ForegroundColor DarkYellow
}

Write-Host "OK: B-Track daily hypothesis chain finished. Bundle: docs/final/artifacts/btrack_llm_input_bundle_latest.json"
