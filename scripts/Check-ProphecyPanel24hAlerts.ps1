#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot 24h alert check for panel promotion candidate.

.DESCRIPTION
  Checks three alert rules against latest artifacts:
  1) price_directional_hit_rate >= 0.60
  2) panel strict_passed && auto_promote_ready == true
  3) shared safety gates passed (btc_csv/model/non-neutral-cap)

  Gate resolution: rows are matched in tracks.shared.gates then root gates[]. If a gate_id is
  absent (e.g. btc_only_crossassist emits only score_btc_csv in the shared slice) but
  shared_all_gates_passed is true, that gate is treated as passed via aggregate (not missing=false).

  Exit code:
    0 = all pass
    1 = one or more alerts failed

  Webhook (failure only): PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL, else OPS_ALARM_WEBHOOK_URL.
  Default routing: POST only when ALERT_1 (hit rate) or ALERT_3 (structural shared gates) fails —
  ALERT_2-only failure (strict_passed / auto_promote_ready) does not POST (reduces noise; exit code still 1).
  Use -IncludeAlert2InWebhook to restore legacy "webhook on any alert failure".
  Use -SkipWebhook to suppress POST (e.g. CI without secrets).
  By default runs lightweight observability refresh (advisory-sweep, Dual-KPI compare) before
  reading artifacts — aligned with run_btrack_daily_hypothesis_chain.ps1. Use -SkipObservabilityRefresh
  for CI or when the daily chain just finished.

  kpi_b_operational_headline: when commander approval JSON is APPROVED_KPI_B_OPERATIONAL_HEADLINE,
  ALERT_1 uses prophecy_runtime_health_thresholds_v1.json (headline >= min_hit_rate_kpi_b_per_date_headline
  OR directional skill floor with n_calls >= 10). Commander O-P29b headline lane (headline_promotion_v1)
  is not auto-promoted from this panel.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [double]$MinHitRate = 0.60,
    [string]$OutJson = "",
    [switch]$AppendLog,
    [switch]$SkipWebhook,
    [switch]$IncludeAlert2InWebhook,
    [switch]$SkipObservabilityRefresh
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

function Read-JsonFile {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing required file: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Read-JsonFileOptional {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        return $null
    }
}

# Observability refresh (non-gating; mirrors daily chain hooks for scheduled panel task).
$obsRefresh = [ordered]@{
    skipped = [bool]$SkipObservabilityRefresh
    steps = @()
}
if (-not $SkipObservabilityRefresh) {
    $perDateDirsPath = Join-Path $WorkspaceRoot "reports\btrack_ensemble_per_date_directions_v1_latest.json"
    $btcDefault = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
    if (-not (Test-Path -LiteralPath $perDateDirsPath) -and (Test-Path -LiteralPath $btcDefault)) {
        Write-Host "==> build_btrack_ensemble_per_date_directions_v1.py (panel advisory prereq)" -ForegroundColor DarkCyan
        py scripts/build_btrack_ensemble_per_date_directions_v1.py --recent-trading-days 30 --target-instrument btc
        $obsRefresh.steps += [ordered]@{ step = "build_per_date_directions"; exit_code = $LASTEXITCODE }
    }
    if (Test-Path -LiteralPath $perDateDirsPath) {
        Write-Host "==> run_btrack_wrong_dir_holdout_v1.py advisory-sweep (panel refresh; non-gating)" -ForegroundColor DarkCyan
        py scripts/run_btrack_wrong_dir_holdout_v1.py advisory-sweep
        $obsRefresh.steps += [ordered]@{ step = "advisory-sweep"; exit_code = $LASTEXITCODE }
        $holdoutManifest = Join-Path $WorkspaceRoot "scripts\build_btrack_holdout_gate_candidate_manifest_v1.py"
        if (Test-Path -LiteralPath $holdoutManifest) {
            py $holdoutManifest --skip-probe-refresh
            $obsRefresh.steps += [ordered]@{ step = "build_btrack_holdout_gate_candidate_manifest_v1"; exit_code = $LASTEXITCODE }
        }
        foreach ($holdoutScript in @(
            "build_btrack_holdout_gate_oos_180d_eval_v1.py",
            "build_btrack_holdout_price_lens_cf_holdout7_v1.py"
        )) {
            $rel = Join-Path $WorkspaceRoot "scripts\$holdoutScript"
            if (Test-Path -LiteralPath $rel) {
                py $rel
                $obsRefresh.steps += [ordered]@{ step = $holdoutScript; exit_code = $LASTEXITCODE }
            }
        }
    } else {
        Write-Host "WARN: Skip advisory-sweep (missing per-date directions): $perDateDirsPath" -ForegroundColor Yellow
        $obsRefresh.steps += [ordered]@{ step = "advisory-sweep"; skipped = "missing_per_date_directions" }
    }

    $compareScript = Join-Path $WorkspaceRoot "scripts\compare_frozen_vs_per_date_combo_panel_v1.py"
    if (Test-Path -LiteralPath $compareScript) {
        Write-Host "==> compare_frozen_vs_per_date_combo_panel_v1.py (Dual-KPI panel compare)" -ForegroundColor DarkCyan
        py $compareScript --min-train-rows 3 --output reports\frozen_vs_per_date_panel_compare_v1_latest.json
        $obsRefresh.steps += [ordered]@{ step = "compare_frozen_vs_per_date_combo_panel_v1"; exit_code = $LASTEXITCODE }
    }

    $kpiBApprovalPath = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_dual_kpi_headline_human_approval_v1_latest.json"
    $kpiBAp = Read-JsonFileOptional -Path $kpiBApprovalPath
    if ($kpiBAp -and ([string]$kpiBAp.decision -eq "APPROVED_KPI_B_OPERATIONAL_HEADLINE")) {
        $btcResolved = $btcDefault
        if (Test-Path -LiteralPath $btcResolved) {
            Write-Host "==> run_btrack_kpi_b_shadow_eval_v1.py (kpi_b_operational_headline observability)" -ForegroundColor DarkCyan
            py scripts/run_btrack_kpi_b_shadow_eval_v1.py --btc-csv $btcResolved
            $obsRefresh.steps += [ordered]@{ step = "kpi_b_shadow_eval"; exit_code = $LASTEXITCODE }
        }
    }
    $missionCSummary = Join-Path $WorkspaceRoot "reports\mission_c_srcdir_expanded_shadow_summary_v1_latest.json"
    if (Test-Path -LiteralPath $missionCSummary) {
        Write-Host "==> build_mission_c_shadow_ops_status_v1.py (Mission C panel observability)" -ForegroundColor DarkCyan
        py scripts/build_mission_c_shadow_ops_status_v1.py
        $obsRefresh.steps += [ordered]@{ step = "build_mission_c_shadow_ops_status_v1"; exit_code = $LASTEXITCODE }
    }
}

$hitPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_daily_operational_latest.json"
$panelPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_promotion_gates_v1_panel_calibrated_latest.json"
$thresholdsPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_runtime_health_thresholds_v1.json"
$kpiBApprovalPath = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_dual_kpi_headline_human_approval_v1_latest.json"
$holdoutGateCandidatePath = Join-Path $WorkspaceRoot "reports\btrack_holdout_gate_candidate_v1_latest.json"
$holdoutGateOosPath = Join-Path $WorkspaceRoot "reports\btrack_holdout_gate_oos_180d_v1_latest.json"
$holdoutCfPath = Join-Path $WorkspaceRoot "reports\btrack_holdout_price_lens_cf_holdout7_v1_latest.json"

$hit = Read-JsonFile -Path $hitPath
$panel = Read-JsonFile -Path $panelPath
$thresholds = Read-JsonFileOptional -Path $thresholdsPath
$kpiBApproval = Read-JsonFileOptional -Path $kpiBApprovalPath

if (-not $hit.metrics) {
    throw "prophecy_hit_rate_eval_daily_operational_latest.json missing metrics (required for ALERT_1)"
}
if ($null -eq $hit.metrics.price_directional_hit_rate) {
    throw "prophecy_hit_rate_eval_daily_operational_latest.json missing metrics.price_directional_hit_rate"
}
$hitRate = [double]($hit.metrics.price_directional_hit_rate)

$kpiBOperationalHeadline = $false
if ($kpiBApproval -and ([string]$kpiBApproval.decision -eq "APPROVED_KPI_B_OPERATIONAL_HEADLINE")) {
    $kpiBOperationalHeadline = $true
}

$alert1Policy = "frozen_default_min_hit_rate"
$alert1ThresholdMin = $MinHitRate
$a1Pass = $hitRate -ge $MinHitRate

if ($kpiBOperationalHeadline -and $thresholds) {
    $alert1Policy = "kpi_b_operational_headline"
    $floorHeadline = [double]$thresholds.min_hit_rate_kpi_b_per_date_headline
    $floorDir = [double]$thresholds.min_directional_hit_rate_kpi_b_operational
    $alert1ThresholdMin = $floorHeadline
    $a1Pass = $hitRate -ge $floorHeadline
    $kpiBShadowPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json"
    $kpiBShadow = Read-JsonFileOptional -Path $kpiBShadowPath
    if ($kpiBShadow -and $kpiBShadow.metrics) {
        $m = $kpiBShadow.metrics
        $dirRate = $null
        $nDir = 0
        if ($null -ne $m.price_hit_rate_on_directional_calls) {
            $dirRate = [double]$m.price_hit_rate_on_directional_calls
        }
        if ($null -ne $m.n_directional_calls) {
            $nDir = [int]$m.n_directional_calls
        }
        if ($dirRate -ne $null -and $nDir -ge 10 -and $dirRate -ge $floorDir) {
            $a1Pass = $true
        }
    }
}

$strictPassed = [bool]$panel.strict_passed
$autoReady = [bool]$panel.auto_promote_ready
$a2Pass = $strictPassed -and $autoReady

$sharedGatesList = @()
if ($panel.tracks -and $panel.tracks.shared -and $panel.tracks.shared.gates) {
    $sharedGatesList = @($panel.tracks.shared.gates)
}
$rootGatesList = @()
if (($panel.PSObject.Properties.Name -contains 'gates') -and $panel.gates) {
    $rootGatesList = @($panel.gates)
}
$mergedGates = [System.Collections.Generic.List[object]]::new()
foreach ($g in $sharedGatesList) { [void]$mergedGates.Add($g) }
foreach ($g in $rootGatesList) { [void]$mergedGates.Add($g) }

$sharedAllPassed = $false
if ($null -ne $panel.shared_all_gates_passed) {
    $sharedAllPassed = [bool]$panel.shared_all_gates_passed
}
$trackSharedAllPassed = $false
if ($panel.tracks -and $panel.tracks.shared -and ($null -ne $panel.tracks.shared.all_gates_passed)) {
    $trackSharedAllPassed = [bool]$panel.tracks.shared.all_gates_passed
}

function Resolve-StructuralGate {
    param([Parameter(Mandatory = $true)][string]$GateId)
    foreach ($x in $mergedGates) {
        if ("$($x.gate_id)" -ne $GateId) { continue }
        return @{
            passed = [bool]$x.passed
            mode   = "row"
        }
    }
    if ($sharedAllPassed -and $trackSharedAllPassed) {
        return @{ passed = $true; mode = "aggregate_tracks_shared" }
    }
    if ($sharedAllPassed) {
        return @{ passed = $true; mode = "aggregate_shared_all" }
    }
    return @{ passed = $false; mode = "missing" }
}

$rNeutral = Resolve-StructuralGate "score_neutral_ratio_cap"
$rModel = Resolve-StructuralGate "hypothesis_non_stub_model"
$rBtcCsv = Resolve-StructuralGate "score_btc_csv_input_present"
$a3Pass = $rNeutral.passed -and $rModel.passed -and $rBtcCsv.passed

$allPass = $a1Pass -and $a2Pass -and $a3Pass

$result = [ordered]@{
    schema = "prophecy_panel_24h_alert_check_v1"
    checked_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    inputs = [ordered]@{
        hit_rate_path = $hitPath
        panel_gate_path = $panelPath
        min_hit_rate = $MinHitRate
        thresholds_path = $thresholdsPath
        kpi_b_approval_path = $kpiBApprovalPath
        holdout_gate_candidate_path = $holdoutGateCandidatePath
        holdout_gate_oos_path = $holdoutGateOosPath
        holdout_price_lens_cf_path = $holdoutCfPath
        observability_refresh = $obsRefresh
        webhook_routing = [ordered]@{
            mode = $(if ($IncludeAlert2InWebhook) { "all_alerts" } else { "performance_and_structural_only" })
            posts_when = $(if ($IncludeAlert2InWebhook) { "any_alert_failed" } else { "alert1_or_alert3_failed" })
        }
    }
    alerts = [ordered]@{
        ALERT_1_PERFORMANCE = [ordered]@{
            passed = $a1Pass
            policy = $alert1Policy
            kpi_b_operational_headline = $kpiBOperationalHeadline
            observed_price_directional_hit_rate = [math]::Round($hitRate, 6)
            threshold_min = $alert1ThresholdMin
            threshold_min_param = $MinHitRate
        }
        ALERT_2_GATE_REGRESSION = [ordered]@{
            passed = $a2Pass
            strict_passed = $strictPassed
            auto_promote_ready = $autoReady
        }
        ALERT_3_STRUCTURAL_RISK = [ordered]@{
            passed = $a3Pass
            score_neutral_ratio_cap_passed = $rNeutral.passed
            score_neutral_ratio_cap_resolution = $rNeutral.mode
            hypothesis_non_stub_model_passed = $rModel.passed
            hypothesis_non_stub_model_resolution = $rModel.mode
            score_btc_csv_input_present_passed = $rBtcCsv.passed
            score_btc_csv_input_present_resolution = $rBtcCsv.mode
        }
    }
    overall_passed = $allPass
}

$resultJson = $result | ConvertTo-Json -Depth 8
Write-Output $resultJson

$outPath = $OutJson.Trim()
if (-not [string]::IsNullOrWhiteSpace($outPath)) {
    $dir = Split-Path -Parent $outPath
    if (-not [string]::IsNullOrWhiteSpace($dir) -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $resultJson | Set-Content -LiteralPath $outPath -Encoding utf8
    Write-Host "WROTE: $outPath" -ForegroundColor Green
}

if ($AppendLog) {
    $logDir = Join-Path $WorkspaceRoot "reports"
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $logPath = Join-Path $logDir "prophecy_panel_24h_alerts_log.jsonl"
    $line = ($resultJson -replace "`r?`n", " ").Trim()
    Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
    Write-Host "APPENDED: $logPath" -ForegroundColor DarkGray
}

if ($allPass) {
    exit 0
}

if (-not $SkipWebhook) {
    $webhookPost = $false
    if ($IncludeAlert2InWebhook) {
        $webhookPost = $true
    }
    else {
        $webhookPost = (-not $a1Pass) -or (-not $a3Pass)
    }

    $webhook = $env:PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL
    if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
        if ($webhookPost) {
            $payload = [ordered]@{
                event = "prophecy_panel_24h_alert_check_failed"
                ts_utc = (Get-Date).ToUniversalTime().ToString("o")
                workspace = $WorkspaceRoot
                overall_passed = $false
                check = ($result | ConvertTo-Json -Depth 10 | ConvertFrom-Json)
            }
            $body = $payload | ConvertTo-Json -Depth 12 -Compress
            try {
                $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json; charset=utf-8" -TimeoutSec 30
                Write-Host "Webhook alert sent: prophecy_panel_24h_alert_check_failed" -ForegroundColor Yellow
            }
            catch {
                Write-Warning "Webhook alert failed: $($_.Exception.Message)"
            }
        }
        else {
            Write-Host "Webhook alert skipped: only ALERT_2 failed (strict_passed / auto_promote_ready). Exit code remains 1. Use -IncludeAlert2InWebhook to POST." -ForegroundColor DarkCyan
        }
    }
    else {
        Write-Host "Webhook alert skipped: no PROPHECY_PANEL_24H_ALERT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL" -ForegroundColor DarkGray
    }
}

exit 1
