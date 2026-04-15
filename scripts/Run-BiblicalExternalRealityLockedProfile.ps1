[CmdletBinding()]
param(
    [string] $LockJson = "docs/final/artifacts/biblical_external_reality_lock_latest.json",
    [int] $RecentTradingDays = 30,
    [bool] $RunExternalDualGateStability = $true,
    [string] $ExternalStabilityYears = "2024,2025,2026",
    [string] $ExternalYearMinOverrides = "",
    [double] $StabilityGoThreshold = 0.75,
    [double] $StabilityGoThresholdOps = 0.67,
    [int] $PromoteConsecutive = 2,
    [bool] $AutoBackfillStabilityYears = $true,
    [int] $BackfillDaysPerYear = 90,
    [string] $StabilityBackfillPredMode = "regime_v2",
    [string] $StabilityYearModeOverrides = "",
    [int] $BuildRetryCount = 2,
    [int] $BuildRetryBackoffSeconds = 2,
    [switch] $UseStagedSearchDefaults,
    [string] $StagedSearchJson = "docs/final/artifacts/biblical_external_dualgate_staged_search_v1_latest.json"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-PythonWithRetry {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$StepName,
        [int]$RetryCount = 0,
        [int]$BackoffSeconds = 2
    )
    $attempt = 0
    while ($true) {
        $attempt += 1
        $proc = Start-Process -FilePath "py" -ArgumentList $Arguments -WorkingDirectory $root -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -eq 0) {
            return
        }
        $isWriterLock = ($proc.ExitCode -eq 3)
        if (-not $isWriterLock -or $attempt -gt ($RetryCount + 1)) {
            exit $proc.ExitCode
        }
        Write-Host ("{0}: writer lock detected, retry {1}/{2} after {3}s" -f $StepName, $attempt, ($RetryCount + 1), $BackoffSeconds)
        Start-Sleep -Seconds $BackoffSeconds
    }
}

$lockPath = if ([System.IO.Path]::IsPathRooted($LockJson)) { $LockJson } else { Join-Path $root $LockJson }
if (-not (Test-Path $lockPath)) { throw "Lock json not found: $lockPath" }
$lock = Get-Content -Raw -Encoding UTF8 $lockPath | ConvertFrom-Json
$p = $lock.selected_params
if (-not $p) { throw "selected_params missing in lock json" }

if ($UseStagedSearchDefaults) {
    $stagedPath = if ([System.IO.Path]::IsPathRooted($StagedSearchJson)) { $StagedSearchJson } else { Join-Path $root $StagedSearchJson }
    if (Test-Path -LiteralPath $stagedPath) {
        try {
            $stagedDoc = Get-Content -LiteralPath $stagedPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $ymo = [string]$stagedDoc.best_year_mode_overrides
            if (-not [string]::IsNullOrWhiteSpace($ymo)) { $StabilityYearModeOverrides = $ymo.Trim() }
        } catch {}
    }
}

$buildArgs = @(
    "scripts/build_btrack_prophecy_score_from_ohlcv.py",
    "--recent-trading-days", "$RecentTradingDays",
    "--bull-reversal-lookback", "$($p.lookback)",
    "--bull-reversal-threshold-pct", "$($p.threshold_pct)",
    "--bull-reversal-target", "$($p.target)",
    "--bull-reversal-require-flow",
    "--bull-reversal-min-flow-score", "$($p.flow_min_score)",
    "--output", "docs/final/artifacts/btrack_prophecy_score_latest.json"
)
if ($null -ne $p.neutral_bps) {
    $buildArgs += @("--neutral-bps", "$($p.neutral_bps)")
}
if ($null -ne $p.bear_relax_enable -and [bool]$p.bear_relax_enable) {
    $buildArgs += "--bear-relax-enable"
}
if ($null -ne $p.two_stage_enable -and [bool]$p.two_stage_enable) {
    $buildArgs += "--two-stage-enable"
}
if ($null -ne $p.bull_reversal_bull_require_non_shock -and [bool]$p.bull_reversal_bull_require_non_shock) {
    $buildArgs += "--bull_reversal_bull_require_non_shock"
}
if ($null -ne $p.bear_relax_require_non_shock -and [bool]$p.bear_relax_require_non_shock) {
    $buildArgs += "--bear_relax_require_non_shock"
}
if ($null -ne $p.year_rebound_require_non_shock -and [bool]$p.year_rebound_require_non_shock) {
    $buildArgs += "--year_rebound_require_non_shock"
}
Write-Host "==> build_btrack_prophecy_score_from_ohlcv.py"
Invoke-PythonWithRetry -Arguments $buildArgs -StepName "build_btrack_prophecy_score_from_ohlcv.py" -RetryCount $BuildRetryCount -BackoffSeconds $BuildRetryBackoffSeconds

$riskOut = "docs/final/artifacts/biblical_external_reality_gate_risk_watch_locked_latest.json"
$mixedOut = "docs/final/artifacts/biblical_external_reality_gate_mixed_locked_latest.json"

Write-Host "==> check_biblical_external_reality_gate_v1.py (risk_watch locked)"
Invoke-PythonWithRetry -Arguments @("scripts/check_biblical_external_reality_gate_v1.py","--reality-profile","biblical_risk_watch","--out",$riskOut) -StepName "check_biblical_external_reality_gate_v1.py risk_watch"

Write-Host "==> check_biblical_external_reality_gate_v1.py (mixed locked)"
Invoke-PythonWithRetry -Arguments @("scripts/check_biblical_external_reality_gate_v1.py","--reality-profile","biblical_mixed_mode","--out",$mixedOut) -StepName "check_biblical_external_reality_gate_v1.py mixed_mode"

if ($RunExternalDualGateStability) {
    Write-Host "==> run_biblical_external_dualgate_stability_v1.py"
    $stabArgs = @(
        "scripts/run_biblical_external_dualgate_stability_v1.py",
        "--years", "$ExternalStabilityYears",
        "--backfill-pred-mode", "$StabilityBackfillPredMode",
        "--stability-go-threshold", "$StabilityGoThreshold",
        "--stability-go-threshold-ops", "$StabilityGoThresholdOps",
        "--promote-consecutive", "$PromoteConsecutive",
        "--backfill-days-per-year", "$BackfillDaysPerYear"
    )
    if ($AutoBackfillStabilityYears) { $stabArgs += "--auto-backfill-years" }
    if ($StabilityYearModeOverrides -and $StabilityYearModeOverrides.Trim().Length -gt 0) { $stabArgs += @("--year-mode-overrides", "$StabilityYearModeOverrides") }
    if ($ExternalYearMinOverrides -and $ExternalYearMinOverrides.Trim().Length -gt 0) { $stabArgs += @("--year-min-overrides", "$ExternalYearMinOverrides") }
    Invoke-PythonWithRetry -Arguments $stabArgs -StepName "run_biblical_external_dualgate_stability_v1.py"
}

$lockOut = [ordered]@{
    schema = "biblical_external_reality_lock_v1"
    generated_at_utc = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    selected_params = $p
    gate_snapshot = [ordered]@{
        risk_watch = (Get-Content -Raw -Encoding UTF8 $riskOut | ConvertFrom-Json)
        mixed_mode = (Get-Content -Raw -Encoding UTF8 $mixedOut | ConvertFrom-Json)
    }
}
$lockOut | ConvertTo-Json -Depth 10 | Set-Content -Path "docs/final/artifacts/biblical_external_reality_lock_latest.json" -Encoding utf8
Write-Host "OK: Locked profile reproduced."
exit 0
