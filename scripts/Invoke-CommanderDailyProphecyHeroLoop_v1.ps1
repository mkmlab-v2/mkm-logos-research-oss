#Requires -Version 5.1
<#
.SYNOPSIS
  Commander daily prophecy hero loop — morning report · midday gen · evening score · evolution.

.DESCRIPTION
  B-track [HYPO] · research_only. No Track A / live trading auto-merge.

  Morning: hypothesis → eval → R-IBL seal → prophecy Telegram (diverse predictions).
  Midday: general prophecy queue refresh (leftover batch lane).
  Evening: OHLCV fetch → briefing score → evolution dry-run → evening_review Telegram.

.EXAMPLE
  pwsh -File scripts/Invoke-CommanderDailyProphecyHeroLoop_v1.ps1 -Phase All
  pwsh -File scripts/Invoke-CommanderDailyProphecyHeroLoop_v1.ps1 -Phase Morning -SkipTelegram
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("Morning", "Midday", "Evening", "All")]
    [string]$Phase = "All",
    [switch]$SkipTelegram,
    [switch]$SkipHypothesisChain,
    [switch]$SkipACodeGovernorEvening,
    [switch]$SkipACodeOperatorLaneEvening,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$dotenv = Join-Path $WorkspaceRoot "scripts\Import-WorkspaceDotEnv_v1.ps1"
if (Test-Path -LiteralPath $dotenv) {
    . $dotenv -WorkspaceRoot $WorkspaceRoot
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$btcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "`n[hero] $Name" -ForegroundColor Cyan
    & $Block
    if ($LASTEXITCODE -ne 0) {
        if ($Strict) { throw "$Name exit $LASTEXITCODE" }
        Write-Warning "$Name exit $LASTEXITCODE (continuing)"
    }
}

$runMorning = $Phase -eq "All" -or $Phase -eq "Morning"
$runMidday = $Phase -eq "All" -or $Phase -eq "Midday"
$runEvening = $Phase -eq "All" -or $Phase -eq "Evening"

if ($runMorning) {
    if (-not $SkipHypothesisChain) {
        Invoke-Step "run_btrack_daily_hypothesis_chain (btc)" {
            & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1") `
                -WorkspaceRoot $WorkspaceRoot -ResearchEvaluationInstrument btc `
                -SkipPanel24hAlertsCheck -SkipProphecyContemplationGemini
        }
    }

    Invoke-Step "run_daily_prophecy_eval_and_report" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\run_daily_prophecy_eval_and_report.ps1") `
            -WorkspaceRoot $WorkspaceRoot -RecentTradingDays 30 -ForceDualLegPanel -SkipTrinityEvolution -BtcCsvPath $btcCsv `
            -IncludeShadowPanelEval -ShadowPanelMode walkforward_aggregate -IncludeCrossLensRagFusion `
            -OperationModeBShadow
    }

    Invoke-Step "build_research_morning_prediction_registry (R-IBL seal)" {
        & $py scripts/build_research_morning_prediction_registry_v1.py
    }

    Invoke-Step "Invoke-TelegramMorningProphecyRefresh" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-TelegramMorningProphecyRefresh_v1.ps1") `
            -WorkspaceRoot $WorkspaceRoot
    }

    if (-not $SkipTelegram) {
        [Environment]::SetEnvironmentVariable("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", "1", "Process")
        [Environment]::SetEnvironmentVariable("MKM_TELEGRAM_MORNING_STYLE", "prophecy", "Process")
        [Environment]::SetEnvironmentVariable("MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL", "1", "Process")
        Invoke-Step "send_telegram prophecy morning" {
            & $py scripts/send_telegram_minimal_ops_digest_v1.py --scheduled-morning --style prophecy --force
        }
    }
}

if ($runMidday) {
    $middayPs1 = Join-Path $WorkspaceRoot "scripts\run_general_prophecy_daily_queue_refresh_v1.ps1"
    if (Test-Path -LiteralPath $middayPs1) {
        Invoke-Step "general_prophecy_daily_queue (midday batch)" {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $middayPs1
        }
    } else {
        Write-Warning "Missing $middayPs1 — skip midday general prophecy"
    }
}

if ($runEvening) {
    $fetchKospi = Join-Path $WorkspaceRoot "scripts\fetch_kospi_yfinance_csv.py"
    if (Test-Path -LiteralPath $fetchKospi) {
        Invoke-Step "fetch_kospi_yfinance_csv (merge long history)" {
            & $py $fetchKospi --merge --start 1990-01-01
        }
    }
    $fetchBtc = Join-Path $WorkspaceRoot "scripts\fetch_btc_yfinance_csv.py"
    if (Test-Path -LiteralPath $fetchBtc) {
        Invoke-Step "fetch_btc_yfinance_csv (merge)" { & $py $fetchBtc --merge }
    }
    $fetchNasdaq = Join-Path $WorkspaceRoot "scripts\fetch_nasdaq_yfinance_csv.py"
    if (Test-Path -LiteralPath $fetchNasdaq) {
        Invoke-Step "fetch_nasdaq_yfinance_csv" { & $py $fetchNasdaq }
    }

    Invoke-Step "score_commander_evening_briefing" {
        & $py scripts/score_commander_evening_briefing_v1.py --skip-kospi-fetch --write-telegram-json
    }

    Invoke-Step "score_research_evening_predictions (R-IBL)" {
        & $py scripts/score_research_evening_predictions_v1.py
    }

    Invoke-Step "run_commander_briefing_evolution (hero evolution dry-run)" {
        & $py scripts/run_commander_briefing_evolution_v1.py
    }

    $juneLoop = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026ProphecyLoop_v1.ps1"
    if (Test-Path -LiteralPath $juneLoop) {
        Invoke-Step "Invoke-KospiJune2026ProphecyLoop (evening score+evolution)" {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $juneLoop `
                -WorkspaceRoot $WorkspaceRoot -Phase Evening -SkipHeavyResearch
        }
    }

    if (-not $SkipACodeGovernorEvening) {
        $aCodeBundle = Join-Path $WorkspaceRoot "scripts\Run-ACodeGovernorResearchBundle_v1.ps1"
        if (Test-Path -LiteralPath $aCodeBundle) {
            $sessionDate = (Get-Date).ToString("yyyy-MM-dd")
            Invoke-Step "Run-ACodeGovernorResearchBundle (evening thin · SkipMultiday)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $aCodeBundle `
                    -WorkspaceRoot $WorkspaceRoot -SessionDate $sessionDate -SkipMultiday
            }
        }
    }

    if (-not $SkipACodeOperatorLaneEvening) {
        $operatorLight = Join-Path $WorkspaceRoot "scripts\Run-ACodeOperatorAssistLaneLightRoutine_v1.ps1"
        if (Test-Path -LiteralPath $operatorLight) {
            $sessionDate = (Get-Date).ToString("yyyy-MM-dd")
            Invoke-Step "Run-ACodeOperatorAssistLaneLightRoutine (evening thin · light profile)" {
                & powershell -NoProfile -ExecutionPolicy Bypass -File $operatorLight `
                    -WorkspaceRoot $WorkspaceRoot -SessionDate $sessionDate
            }
        }
    }

    if (-not $SkipTelegram) {
        [Environment]::SetEnvironmentVariable("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", "1", "Process")
        Invoke-Step "send_telegram evening_review" {
            & $py scripts/send_telegram_minimal_ops_digest_v1.py --style evening_review --force --allow-legacy-style
        }
    }
}

Write-Host "`n[hero] OK phase=$Phase" -ForegroundColor Green
exit 0
