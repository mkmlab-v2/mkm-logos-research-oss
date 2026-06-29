#Requires -Version 5.1
<#
.SYNOPSIS
  June 2026 KOSPI weekend B-track research bundle (Logos · BTC · WF · macro PoC).

.DESCRIPTION
  research_only · auto_apply=false · no Track A / live trading merge.
  Typical runtime: Logos ~2m · BTC ~6m · WF fold trace ~25m · macro PoC ~1m.

.EXAMPLE
  pwsh -File scripts/Invoke-KospiJune2026WeekendResearchBundle_v1.ps1
  pwsh -File scripts/Invoke-KospiJune2026WeekendResearchBundle_v1.ps1 -SkipWf
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$YearMonth = "2026-06",
    [switch]$SkipLogos,
    [switch]$SkipBtc,
    [switch]$SkipWf,
    [switch]$SkipMacro,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$startedUtc = (Get-Date).ToUniversalTime().ToString("o")
$steps = [System.Collections.Generic.List[object]]::new()

function Invoke-Step([string]$Name, [scriptblock]$Block) {
    Write-Host "`n[weekend-kospi] $Name" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Block
    $code = $LASTEXITCODE
    $sw.Stop()
    $steps.Add([ordered]@{
        name       = $Name
        exit_code  = $code
        elapsed_ms = [int]$sw.ElapsedMilliseconds
    }) | Out-Null
    if ($code -ne 0) {
        if ($Strict) { throw "$Name exit $code" }
        Write-Warning "$Name exit $code (continuing)"
    }
}

$calendarJson = Join-Path $WorkspaceRoot "reports\kospi_june2026_daily_prophecy_calendar_v1.json"
$ymTag = $YearMonth.Replace("-", "")
if ($YearMonth -ne "2026-06") {
    $calendarJson = Join-Path $WorkspaceRoot "reports\kospi_${ymTag}_daily_prophecy_calendar_v1.json"
}

if (-not $SkipLogos) {
    Invoke-Step "logos_gold_q09_kospi_report_chain" {
        & $py scripts/run_logos_gold_q09_kospi_report_chain_v1.py
    }
}

if (-not $SkipBtc) {
    Invoke-Step "Run-BtcMultilensResearchCrossCheck (-SkipHorizon)" {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Run-BtcMultilensResearchCrossCheck_v1.ps1") -SkipHorizon
    }
}

if (-not $SkipWf) {
    $fetchKospi = Join-Path $WorkspaceRoot "scripts\fetch_kospi_yfinance_csv.py"
    $fetchEndKst = (Get-Date).AddDays(1).ToString("yyyy-MM-dd")
    if (Test-Path -LiteralPath $fetchKospi) {
        Invoke-Step "fetch_kospi_yfinance_csv (merge for WF history)" {
            & $py $fetchKospi --merge --start 1990-01-01 --end $fetchEndKst --fill-recent-gaps
        }
    }
    Invoke-Step "build_kospi_june2026_wf_pinned_variant_fold_trace (RQ-032)" {
        & $py scripts/build_kospi_june2026_wf_pinned_variant_fold_trace_v1.py
    }
    Invoke-Step "build_kospi_june2026_wf_prefilter_drift_digest" {
        & $py scripts/build_kospi_june2026_wf_prefilter_drift_digest_v1.py
    }
}

if (-not $SkipMacro -and (Test-Path -LiteralPath $calendarJson)) {
    Invoke-Step "build_kospi_june2026_macro_daily_refresh_poc" {
        & $py scripts/build_kospi_june2026_macro_daily_refresh_poc_v1.py `
            --calendar-json $calendarJson `
            --year-month $YearMonth `
            --refresh-macro-backfill `
            --no-write-counter-calendar
    }
}

Invoke-Step "Verify-KospiJune2026ProphecyEveningTask (schedule sanity)" {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Verify-KospiJune2026ProphecyEveningTask.ps1")
}

$failCount = @($steps | Where-Object { $_.exit_code -ne 0 }).Count
$summary = [ordered]@{
    schema           = "kospi_june2026_weekend_research_bundle_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    started_at_utc   = $startedUtc
    hypothesis_tier  = "B"
    research_only    = $true
    auto_apply       = $false
    track_wall       = "no_track_a_live_auto_merge"
    year_month       = $YearMonth
    steps            = @($steps)
    steps_failed     = $failCount
    ok               = ($failCount -eq 0)
}

$outJson = Join-Path $WorkspaceRoot "reports\kospi_june2026_weekend_research_bundle_v1_latest.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outJson -Encoding utf8
Write-Host "Wrote $outJson ok=$($summary.ok) failed=$failCount" -ForegroundColor $(if ($summary.ok) { "Green" } else { "Yellow" })

if ($Strict -and $failCount -gt 0) { exit 1 }
exit 0
