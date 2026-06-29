# KOSPI lens ablation walk-forward chain [HYPO][research_only]
param(
    [string]$DateFrom = "1996-12-11",
    [string]$DateTo = "2026-06-05",
    [string]$WorkspaceRoot = (Split-Path $PSScriptRoot -Parent),
    [switch]$SkipJsonlBuild,
    [switch]$SkipMacroBackfill,
    [switch]$SkipAblation,
    [switch]$IncludeMacroPerDate,
    [switch]$BuildSnapshotVsWalkforwardSummary
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

function Invoke-Step([string]$Label, [scriptblock]$Block) {
    Write-Host "==> $Label"
    & $Block
    if ($LASTEXITCODE -ne 0) {
        throw "$Label exit $LASTEXITCODE"
    }
}

if (-not $SkipJsonlBuild) {
    Invoke-Step "build_myeongni_jsonl_from_manseryeok_session (full window)" {
        py scripts/build_myeongni_jsonl_from_manseryeok_session_v1.py `
            --date-from $DateFrom `
            --date-to $DateTo `
            --calendar-mode krx_weekdays
    }
}

if (-not $SkipMacroBackfill -and $IncludeMacroPerDate) {
    Invoke-Step "backfill_macro_risk_forward_log_from_ohlcv (research)" {
        py scripts/backfill_macro_risk_forward_log_from_ohlcv_v1.py `
            --date-from $DateFrom `
            --date-to $DateTo
    }
}

if (-not $SkipAblation) {
    $macroFlag = @()
    if ($IncludeMacroPerDate) {
        $macroFlag = @("--include-macro-per-date")
    }
    Invoke-Step "run_kospi_lens_ablation_backtest (per_date_jsonl)" {
        py scripts/run_kospi_lens_ablation_backtest_v1.py `
            --panel-csv reports/btrack_session_myeongni_panel_full_window_v1.csv `
            --date-from $DateFrom `
            --date-to $DateTo `
            --lens-source per_date_jsonl `
            @macroFlag `
            --also-window "2025-11-01:2026-05-30:recent140d"
    }
}

if ($BuildSnapshotVsWalkforwardSummary) {
    Invoke-Step "build_kospi_lens_ablation_snapshot_vs_walkforward" {
        $skipMacro = @()
        if (-not $IncludeMacroPerDate) {
            $skipMacro = @("--skip-macro")
        }
        py scripts/build_kospi_lens_ablation_snapshot_vs_walkforward_v1.py @skipMacro
    }
}

Write-Host "OK: KOSPI lens ablation walkforward chain finished."
