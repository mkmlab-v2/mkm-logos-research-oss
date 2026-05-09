<#
.SYNOPSIS
  Refreshes Track B weekly gate, promotion precheck draft, compression leaderboard, and B-track weekly consolidation (research lane).

.NOTES
  Run from repo root.
  Default mode runs lightweight weekly refresh first (-SkipSsmSmoke -SkipCosine), then precheck/leaderboard/consolidation.
  Add -IncludeExtendedStress (and optional -WeeklyB2Included) for heavy split stress runs in the same rollup.
  To skip refresh and only rebuild downstream artifacts, use -SkipWeeklyRefresh.
  Example after measuring extended stress (~16.5m wall): -PromotionWeeklyRefreshMs 987805 -OperationalRuntimeBudgetMs 1200000 -WeeklyExitCode 0 -WeeklyB2Included
#>
[CmdletBinding()]
param(
    # Skip weekly refresh and only rebuild downstream artifacts.
    [switch] $SkipWeeklyRefresh,
    # If RunWeeklyRefresh=true, include extended stress splits (A/B1 and optionally B2).
    [switch] $IncludeExtendedStress,
    # Measured wall ms for full extended stress chain (e.g. ranking+replay+base grid + split A/B1/B2). Omit for null runtime_budget_ok.
    [int] $PromotionWeeklyRefreshMs = -1,
    # Ceiling vs PromotionWeeklyRefreshMs (default script default 300000). Use 1200000 for ~20m research extended runs.
    [int] $OperationalRuntimeBudgetMs = -1,
    [Nullable[int]] $WeeklyExitCode = $null,
    [switch] $WeeklyB2Included
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Step([string]$Label, [string[]]$PyArgs) {
    Write-Host "==> $Label" -ForegroundColor Cyan
    $p = Start-Process -FilePath "py" -ArgumentList $PyArgs -WorkingDirectory $root -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { throw "py failed (exit $($p.ExitCode)): $Label" }
}

# Optionally run fresh weekly refresh first so rollup reflects current state.
$measuredWeeklyMs = $null
$measuredWeeklyExit = $null
if (-not $SkipWeeklyRefresh) {
    $refreshArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "scripts/Run-TrackBWeeklyRefresh.ps1",
        "-SkipSsmSmoke",
        "-SkipCosine"
    )
    if ($IncludeExtendedStress) {
        $refreshArgs += "-IncludeExtendedStressGrid"
        if ($WeeklyB2Included) {
            $refreshArgs += "-IncludeExtendedStressB2"
        }
        $refreshArgs += "-IncludeStressBenchmarkSummary"
    }
    Write-Host "==> run_trackb_weekly_refresh" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & powershell @refreshArgs
    $measuredWeeklyExit = $LASTEXITCODE
    $sw.Stop()
    $measuredWeeklyMs = [int]$sw.ElapsedMilliseconds
    if ($measuredWeeklyExit -ne 0) {
        throw "weekly refresh failed (exit $measuredWeeklyExit)"
    }
}

if ($SkipWeeklyRefresh) {
    Invoke-Step "run_trackb_weekly_gate_recheck" @("scripts/run_trackb_weekly_gate_recheck.py")
}
$precheckArgs = @("scripts/build_trackb_promotion_precheck_draft_v1.py")
if ($PromotionWeeklyRefreshMs -ge 0) {
    $precheckArgs += "--weekly-refresh-ms", "$PromotionWeeklyRefreshMs"
} elseif ($null -ne $measuredWeeklyMs) {
    $precheckArgs += "--weekly-refresh-ms", "$measuredWeeklyMs"
}
if ($OperationalRuntimeBudgetMs -ge 0) {
    $precheckArgs += "--operational-runtime-budget-ms", "$OperationalRuntimeBudgetMs"
}
if ($null -ne $WeeklyExitCode) {
    $precheckArgs += "--weekly-exit-code", "$WeeklyExitCode"
} elseif ($null -ne $measuredWeeklyExit) {
    $precheckArgs += "--weekly-exit-code", "$measuredWeeklyExit"
}
if ($WeeklyB2Included) {
    $precheckArgs += "--weekly-b2-included"
}
Invoke-Step "build_trackb_promotion_precheck_draft_v1" $precheckArgs
Invoke-Step "build_btrack_compression_leaderboard_v1" @("scripts/build_btrack_compression_leaderboard_v1.py")
Invoke-Step "build_btrack_weekly_consolidation_v1" @("scripts/build_btrack_weekly_consolidation_v1.py")
Invoke-Step "build_btrack_rollup_ops_snapshot_v1" @("scripts/build_btrack_rollup_ops_snapshot_v1.py")

# Alert on ops snapshot degradation, but don't fail rollup on expected warning exit(1).
Write-Host "==> alert_btrack_rollup_ops_snapshot_v1" -ForegroundColor Cyan
$alertProc = Start-Process -FilePath "py" -ArgumentList @("scripts/alert_btrack_rollup_ops_snapshot_v1.py", "--always-log") -WorkingDirectory $root -Wait -PassThru -NoNewWindow
if ($alertProc.ExitCode -notin @(0, 1)) {
    throw "py failed (exit $($alertProc.ExitCode)): alert_btrack_rollup_ops_snapshot_v1"
}
if ($alertProc.ExitCode -eq 1) {
    Write-Host "Rollup ops snapshot warning detected (alert status)." -ForegroundColor Yellow
}

if ($null -ne $measuredWeeklyMs) {
    Write-Host "Weekly refresh measured: exit=$measuredWeeklyExit elapsed_ms=$measuredWeeklyMs" -ForegroundColor DarkCyan
}
Write-Host "Rollup done: trackb_weekly_gate_recheck_latest.json, trackb_promotion_precheck_draft_latest.json, btrack_compression_leaderboard_latest.json, btrack_weekly_consolidation_latest.json, btrack_rollup_ops_snapshot_latest.json, btrack_rollup_ops_alert_latest.json" -ForegroundColor Green
