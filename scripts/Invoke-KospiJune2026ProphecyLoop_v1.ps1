#Requires -Version 5.1
<#
.SYNOPSIS
  June 2026 KOSPI daily prophecy — calendar build · evening score · evolution [HYPO].

.DESCRIPTION
  B-track research_only. Hooks into Commander evening hero loop optionally.
  Long-term memory: run athena_checkpoint after successful evening pass.

.EXAMPLE
  pwsh -File scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1 -Phase All
  pwsh -File scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1 -Phase Evening
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("Morning", "Evening", "All")]
    [string]$Phase = "All",
    [string]$YearMonth = "2026-06",
    [switch]$SkipPanelRebuild,
    [switch]$SkipHeavyResearch,
    [switch]$RefreshWalkforward,
    [switch]$SkipGovernorObs,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$todayKst = (Get-Date).ToString("yyyy-MM-dd")

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "`n[june-kospi] $Name" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        if ($Strict) { throw "$Name exit $LASTEXITCODE" }
        Write-Warning "$Name exit $LASTEXITCODE (continuing)"
    }
}

$runMorning = $Phase -eq "All" -or $Phase -eq "Morning"
$runEvening = $Phase -eq "All" -or $Phase -eq "Evening"
$ymTag = $YearMonth.Replace("-", "")
$calendarJson = Join-Path $WorkspaceRoot "reports\kospi_${ymTag}_daily_prophecy_calendar_v1.json"
if (-not (Test-Path -LiteralPath $calendarJson) -and $YearMonth -eq "2026-06") {
    $calendarJson = Join-Path $WorkspaceRoot "reports\kospi_june2026_daily_prophecy_calendar_v1.json"
}

function Invoke-June4AiReportChain {
    if ($YearMonth -ne "2026-06") { return }
    Invoke-Step "kospi_june_4ai_prophecy_overlay" {
        & $py scripts/kospi_june_4ai_prophecy_overlay_v1.py --calendar-json $calendarJson
    }
    Invoke-Step "render_kospi_june_4ai_prophecy_report" {
        & $py scripts/render_kospi_june_4ai_prophecy_report_v1.py
    }
}

if ($runMorning) {
    $panelArgs = @("--year-month", $YearMonth)
    if ($SkipPanelRebuild) { $panelArgs += "--skip-panel-rebuild" }
    Invoke-Step "build_kospi_daily_prophecy_calendar ($YearMonth)" {
        & $py scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py @panelArgs --profile v2_multilens --seal-date $todayKst
    }
    Invoke-June4AiReportChain
}

if ($runEvening) {
    $fetchKospi = Join-Path $WorkspaceRoot "scripts\fetch_kospi_yfinance_csv.py"
    if (Test-Path -LiteralPath $fetchKospi) {
        Invoke-Step "fetch_kospi_yfinance_csv (merge long history)" {
            & $py $fetchKospi --merge --start 1990-01-01
        }
    }

    $gapAudit = Join-Path $WorkspaceRoot "scripts\audit_kospi_csv_gaps_v1.py"
    if (Test-Path -LiteralPath $gapAudit) {
        Invoke-Step "audit_kospi_csv_gaps (June window)" {
            & $py $gapAudit --window-start "2026-06-01"
        }
    }

    Invoke-Step "eval_kospi_daily_prophecy ($YearMonth)" {
        & $py scripts/eval_kospi_june2026_daily_prophecy_v1.py --calendar-json $calendarJson
    }

    if ($YearMonth -eq "2026-06") {
        Invoke-Step "kospi_june_4ai_prophecy_overlay (pre-evolution KPI)" {
            & $py scripts/kospi_june_4ai_prophecy_overlay_v1.py --calendar-json $calendarJson
        }
        $backtestScript = Join-Path $WorkspaceRoot "scripts\run_kospi_multilens_blend_backtest_v1.py"
        if (Test-Path -LiteralPath $backtestScript) {
            Invoke-Step "run_kospi_multilens_blend_backtest (shadow refresh)" {
                & $py $backtestScript --date-from 2025-11-01 --date-to 2026-05-30
            }
        }
        Invoke-Step "run_kospi_june2026_weight_candidate_compare (dry-run)" {
            & $py scripts/run_kospi_june2026_weight_candidate_compare_v1.py --year-month $YearMonth
        }
        Invoke-Step "build_kospi_june2026_promotion_readiness" {
            & $py scripts/build_kospi_june2026_promotion_readiness_v1.py --year-month $YearMonth
        }
        Invoke-Step "build_kospi_june2026_human_apply_review_bundle" {
            & $py scripts/build_kospi_june2026_human_apply_review_bundle_v1.py
        }
        $walkJson = Join-Path $WorkspaceRoot "reports\kospi_multilens_walkforward_backtest_latest.json"
        $walkStale = $true
        if (Test-Path -LiteralPath $walkJson) {
            $ageDays = ((Get-Date) - (Get-Item -LiteralPath $walkJson).LastWriteTime).TotalDays
            if ($ageDays -lt 7) { $walkStale = $false }
        }
        if ($RefreshWalkforward -or $walkStale) {
            $walkScript = Join-Path $WorkspaceRoot "scripts\run_kospi_multilens_walkforward_backtest_v1.py"
            if (Test-Path -LiteralPath $walkScript) {
                Invoke-Step "run_kospi_multilens_walkforward_backtest (weekly/stale refresh)" {
                    & $py $walkScript --train-days 1260 --test-days 252 --step-days 126
                }
                Invoke-Step "run_kospi_june2026_weight_candidate_compare (post-walkforward)" {
                    & $py scripts/run_kospi_june2026_weight_candidate_compare_v1.py --year-month $YearMonth
                }
                Invoke-Step "build_kospi_june2026_promotion_readiness (post-walkforward)" {
                    & $py scripts/build_kospi_june2026_promotion_readiness_v1.py --year-month $YearMonth
                }
            }
        }
        if (-not $SkipHeavyResearch) {
            Invoke-Step "backfill_macro_risk_forward_log_from_ohlcv (research)" {
                & $py scripts/backfill_macro_risk_forward_log_from_ohlcv_v1.py --date-from 2026-01-01 --date-to 2026-04-30
            }
            Invoke-Step "run_three_lens_horizon_empirical_eval_v2 (B-track kospi+btc)" {
                & $py scripts/run_three_lens_horizon_empirical_eval_v2.py --instrument both --date-from 2026-01-01 --date-to 2026-04-30
            }
        } else {
            Write-Host "[june-kospi] SkipHeavyResearch: macro backfill + horizon v2 생략" -ForegroundColor DarkYellow
        }
        Invoke-Step "run_kospi_june2026_prophecy_evolution (dry-run)" {
            & $py scripts/run_kospi_june2026_prophecy_evolution_v1.py
        }
    }

    Invoke-Step "rebuild calendar (post-evolution weights unchanged in dry-run)" {
        & $py scripts/build_kospi_june2026_daily_prophecy_calendar_v1.py --year-month $YearMonth --skip-panel-rebuild --profile v2_multilens
    }

    Invoke-June4AiReportChain

    if (-not $SkipGovernorObs) {
        $govBundle = Join-Path $WorkspaceRoot "scripts\Run-ACodeGovernorResearchBundle_v1.ps1"
        $govObs = Join-Path $WorkspaceRoot "scripts\build_a_code_governor_knob_evening_observation_v1.py"
        if (Test-Path -LiteralPath $govBundle) {
            Invoke-Step "Run-ACodeGovernorResearchBundle (replay+gate+obs)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $govBundle `
                    -WorkspaceRoot $WorkspaceRoot -SessionDate $todayKst
            }
        } elseif (Test-Path -LiteralPath $govObs) {
            Invoke-Step "a_code_governor_knob_evening_observation (RQ-028 [HYPO])" {
                & $py $govObs --session-date $todayKst
            }
        }
        $govJson = Join-Path $WorkspaceRoot "reports\a_code_governor_knob_evening_observation_v1_latest.json"
        if (Test-Path -LiteralPath $govJson) {
            try {
                $gov = Get-Content -LiteralPath $govJson -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($gov.evening_append_line) {
                    Write-Host $gov.evening_append_line -ForegroundColor DarkCyan
                }
            } catch {
                Write-Warning "governor evening observation parse failed: $_"
            }
        }
        $gateJson = Join-Path $WorkspaceRoot "reports\a_code_governor_promotion_gate_v1_latest.json"
        if (Test-Path -LiteralPath $gateJson) {
            try {
                $gate = Get-Content -LiteralPath $gateJson -Raw -Encoding UTF8 | ConvertFrom-Json
                $decision = $gate.summary.decision
                if ($decision) {
                    Write-Host "[june-kospi] a-code gate: $decision (non-gating [HYPO])" -ForegroundColor DarkYellow
                }
            } catch {
                Write-Warning "governor promotion gate parse failed: $_"
            }
        }
    }

    Invoke-Step "athena_checkpoint (long-term memory)" {
        & $py scripts/athena_checkpoint.py "$YearMonth 코스피 4AI 종합보고서+evening score 완료 [HYPO]"
    }
}

$readinessPath = Join-Path $WorkspaceRoot "reports\kospi_june2026_promotion_readiness_latest.json"
if (Test-Path -LiteralPath $readinessPath) {
    try {
        $rd = Get-Content -LiteralPath $readinessPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $fs = $rd.forward_scoring
        Write-Host (
            "[june-kospi] readiness: n_scored=$($fs.n_scored)/$($fs.min_required) " +
            "gate_eta=$($fs.projected_gate_session_date) verdict=$($rd.verdict_ko)"
        ) -ForegroundColor Green
    } catch {
        Write-Warning "readiness summary parse failed: $_"
    }
}

Write-Host "`n[june-kospi] done Phase=$Phase YearMonth=$YearMonth" -ForegroundColor Green
