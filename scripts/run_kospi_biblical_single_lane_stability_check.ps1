Param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$LockJson = "docs/final/artifacts/biblical_external_reality_lock_latest.json",
    [string]$StabilityJson = "docs/final/artifacts/biblical_external_dualgate_stability_v1_backfill90_bullgrid_probe.json",
    [string]$OutJson = "docs/final/artifacts/kospi_biblical_single_lane_commercial_gate_autonomous_latest.json",
    [string]$RecentCompareOutJson = "docs/final/artifacts/_tmp_kospi_biblical_single_lane_commercial_gate_recent_min30.json",
    [string]$StatusOutJson = "docs/final/artifacts/kospi_biblical_single_lane_stability_status_latest.json",
    [string]$ProphecyOutJson = "docs/final/artifacts/kospi_biblical_prophecy_output_v2_latest.json",
    [string]$ModeDivergenceOutJson = "docs/final/artifacts/kospi_biblical_mode_divergence_report_v1_latest.json",
    [int]$CanonicalMinN = 30,
    [int]$StreakRequired = 3,
    [double]$StreakMinSpacingHours = 24.0,
    [switch]$PreferRecentOnDivergence,
    [switch]$SyncBitcoinTradingHook,
    [switch]$SyncTwoTrackSnapshot,
    [switch]$Sync2050Prophecy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Send-DivergenceAlert {
    param(
        [hashtable]$Report
    )
    $webhook = $env:KOSPI_BIBLICAL_DIVERGENCE_ALARM_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:KOSPI_BIBLICAL_STABILITY_ALARM_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        return
    }
    try {
        $payload = [ordered]@{
            event = "kospi_biblical_mode_divergence_alert"
            ts_utc = ([DateTimeOffset]::UtcNow).ToString("o")
            source = "run_kospi_biblical_single_lane_stability_check.ps1"
            details = $Report
        }
        $json = $payload | ConvertTo-Json -Depth 10 -Compress
        $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 20
    }
    catch {
        Write-Host "[stability-check] divergence alert send failed: $($_.Exception.Message)"
    }
}

if (-not (Test-Path -LiteralPath $WorkspaceRoot)) {
    throw "Workspace root not found: $WorkspaceRoot"
}

Push-Location $WorkspaceRoot
try {
    $runner = "scripts/report_kospi_biblical_single_lane_commercial_gate_v1.py"
    $prophecyBuilder = "scripts/build_kospi_biblical_prophecy_output_v2.py"
    if (-not (Test-Path -LiteralPath $runner)) {
        throw "Runner script not found: $runner"
    }
    if (-not (Test-Path -LiteralPath $prophecyBuilder)) {
        throw "Prophecy builder script not found: $prophecyBuilder"
    }

    py $runner `
        --lock-json $LockJson `
        --stability-json $StabilityJson `
        --out $OutJson `
        --min-n $CanonicalMinN `
        --streak-required $StreakRequired `
        --streak-min-spacing-hours $StreakMinSpacingHours
    if ($LASTEXITCODE -ne 0) {
        throw "Gate runner failed with exit code $LASTEXITCODE"
    }

    # Build a recent-priority comparison report (min_n=30) to detect mode drift.
    py $runner `
        --lock-json $LockJson `
        --stability-json $StabilityJson `
        --out $RecentCompareOutJson `
        --min-n 30 `
        --streak-required $StreakRequired `
        --streak-min-spacing-hours $StreakMinSpacingHours
    if ($LASTEXITCODE -ne 0) {
        throw "Recent compare gate runner failed with exit code $LASTEXITCODE"
    }

    $divergenceBuilder = "scripts/build_kospi_biblical_mode_divergence_report_v1.py"
    if (-not (Test-Path -LiteralPath $divergenceBuilder)) {
        throw "Mode divergence builder script not found: $divergenceBuilder"
    }
    py $divergenceBuilder --canonical $OutJson --recent $RecentCompareOutJson --out $ModeDivergenceOutJson
    if ($LASTEXITCODE -ne 0) {
        throw "Mode divergence report build failed with exit code $LASTEXITCODE"
    }

    $divergence = Get-Content -LiteralPath $ModeDivergenceOutJson -Raw -Encoding utf8 | ConvertFrom-Json
    if ($PreferRecentOnDivergence -and [bool]$divergence.alert -and [bool]$divergence.diff.mode_changed) {
        Copy-Item -LiteralPath $RecentCompareOutJson -Destination $OutJson -Force
        $divergence = Get-Content -LiteralPath $ModeDivergenceOutJson -Raw -Encoding utf8 | ConvertFrom-Json
        Write-Host "[stability-check] divergence safe-mode: promoted recent gate output to canonical"
    }
    if ([bool]$divergence.alert) {
        $reportPayload = [ordered]@{
            canonical_mode = [string]$divergence.canonical.mode
            recent_mode = [string]$divergence.recent.mode
            reasons = @($divergence.alert_reasons)
            accuracy_gap_abs = [double]$divergence.diff.accuracy_gap_abs
            dominant_share_gap_abs = [double]$divergence.diff.dominant_share_gap_abs
            canonical_stage = [string]$divergence.canonical.stage
            recent_stage = [string]$divergence.recent.stage
        }
        $p2050 = "docs/final/artifacts/prophecy_2050_two_track_v1_latest.json"
        if (Test-Path -LiteralPath $p2050) {
            try {
                $d2050 = Get-Content -LiteralPath $p2050 -Raw -Encoding utf8 | ConvertFrom-Json
                $band = $null
                if ($d2050.track_a_trading_theory -and $d2050.track_a_trading_theory.operational_bands) {
                    $band = @($d2050.track_a_trading_theory.operational_bands) | Where-Object { $_.period -eq "2026-2030" } | Select-Object -First 1
                }
                $reportPayload["prophecy_2050"] = [ordered]@{
                    generated_at_utc = [string]$d2050.generated_at_utc
                    track_a_today_action = [string]$d2050.track_a_trading_theory.current_state.operator_brief.today_action
                    track_a_gate_stage = [string]$d2050.track_a_trading_theory.current_state.gate_stage
                    era_2026_2030_thesis = if ($band) { [string]$band.thesis } else { $null }
                }
            }
            catch {
                # Best-effort enrichment only.
            }
        }
        Send-DivergenceAlert -Report $reportPayload
    }

    $gate = Get-Content -LiteralPath $OutJson -Raw -Encoding utf8 | ConvertFrom-Json
    $stability = $gate.stability
    $nowUtc = [DateTimeOffset]::UtcNow
    $latestTs = [DateTimeOffset]::Parse($stability.latest_ts_utc)
    $nextEligible = $latestTs.AddHours([double]$stability.streak_min_spacing_hours)
    $remainingHours = [Math]::Max(0.0, ($nextEligible - $nowUtc).TotalHours)

    $blockers = @($gate.blockers)
    $pre = [bool]$gate.precommercial_ready
    $sg = [bool]$stability.stability_go
    $liveReasons = @()
    if (-not $pre) { $liveReasons += "precommercial_ready=false" }
    if (-not $sg) { $liveReasons += "stability_go=false (streak not complete)" }
    if ($blockers.Count -gt 0) { $liveReasons += ("blockers: " + ($blockers -join ", ")) }
    $liveAllowed = ($pre -and $sg -and ($blockers.Count -eq 0))

    if ($liveAllowed) {
        $livePhase = "live_eligible"
    }
    elseif ($sg) {
        $livePhase = "stable"
    }
    elseif ($pre) {
        $livePhase = "precommercial"
    }
    else {
        $livePhase = "research"
    }

    $status = [ordered]@{
        schema = "kospi_biblical_single_lane_stability_status_v1"
        generated_at_utc = $nowUtc.ToString("o")
        gate_path = (Resolve-Path -LiteralPath $OutJson).Path
        stage = [string]$gate.stage
        precommercial_ready = $pre
        blockers = $blockers
        ready_streak = [int]$stability.current_ready_streak
        streak_required = [int]$stability.streak_required
        stability_go = $sg
        streak_min_spacing_hours = [double]$stability.streak_min_spacing_hours
        latest_streak_ts_utc = [string]$stability.latest_ts_utc
        next_eligible_streak_ts_utc = $nextEligible.ToString("o")
        remaining_hours_until_next_eligible = [Math]::Round($remainingHours, 3)
        recommendation = if ($stability.stability_go) { "stable" } else { "wait_for_next_time_window" }
        live_trading = [ordered]@{
            lane = "biblical_only"
            policy = "Biblical lane only; no myeongri/sasang fusion; order hook requires human limits + kill switch"
            phase = $livePhase
            allowed = $liveAllowed
            reasons_if_blocked = @($liveReasons)
            note = "allowed=true means gate-evidence only; broker integration and sizing are out of band."
        }
    }

    $status | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatusOutJson -Encoding utf8

    py $prophecyBuilder --gate-json $OutJson --status-json $StatusOutJson --out $ProphecyOutJson
    if ($LASTEXITCODE -ne 0) {
        throw "Prophecy output build failed with exit code $LASTEXITCODE"
    }

    if ($SyncBitcoinTradingHook) {
        $syncer = "scripts/sync_biblical_lane_hook_to_bitcoin_trading.py"
        if (-not (Test-Path -LiteralPath $syncer)) {
            throw "Bitcoin hook sync script not found: $syncer"
        }
        py $syncer
        if ($LASTEXITCODE -ne 0) {
            throw "Bitcoin trading hook sync failed with exit code $LASTEXITCODE"
        }
        Write-Host "[stability-check] bitcoin-trading hook synced (biblical_single_lane_trading_hook_v1_latest.json)"
    }

    if ($SyncTwoTrackSnapshot) {
        $twoTrackBuilder = "scripts/build_prophecy_two_track_snapshot_v1.py"
        if (-not (Test-Path -LiteralPath $twoTrackBuilder)) {
            throw "Two-track snapshot builder script not found: $twoTrackBuilder"
        }
        py $twoTrackBuilder
        if ($LASTEXITCODE -ne 0) {
            throw "Two-track snapshot build failed with exit code $LASTEXITCODE"
        }
        Write-Host "[stability-check] two-track snapshot updated (prophecy_two_track_snapshot_v1_latest.json)"
    }

    if ($Sync2050Prophecy) {
        $builder2050 = "scripts/build_prophecy_2050_two_track_v1.py"
        if (-not (Test-Path -LiteralPath $builder2050)) {
            throw "2050 prophecy builder script not found: $builder2050"
        }
        py $builder2050
        if ($LASTEXITCODE -ne 0) {
            throw "2050 prophecy build failed with exit code $LASTEXITCODE"
        }
        Write-Host "[stability-check] 2050 prophecy updated (prophecy_2050_two_track_v1_latest.json)"
    }

    Write-Host ("[stability-check] status written: {0}" -f $StatusOutJson)
    Write-Host ("[stability-check] prophecy output written: {0}" -f $ProphecyOutJson)
    Write-Host ("[stability-check] mode divergence report written: {0}" -f $ModeDivergenceOutJson)
    Write-Host ("[stability-check] stage={0} streak={1}/{2} stability_go={3}" -f $status.stage, $status.ready_streak, $status.streak_required, $status.stability_go)
}
finally {
    Pop-Location
}
