<#
.SYNOPSIS
  Emotion-weighted memory weekly chain runner.

.DESCRIPTION
  1) Build emotion-weighted memory event JSONL
  2) Evaluate weekly impact report JSON

  Default input uses docs/final/dummy_swarm_score.jsonl for safe smoke.
  In operations, pass -InputJsonl with real sentiment feed JSONL.
#>
param(
    [string]$InputJsonl = "C:\workspace\docs\final\dummy_swarm_score.jsonl",
    [string]$LabelsJsonl = "",
    [string]$OutEventsJsonl = "C:\workspace\projects\bitcoin-trading\memory\v2\emotion_weighted_memory_events_latest.jsonl",
    [string]$OutWeeklyReportJson = "C:\workspace\docs\final\artifacts\emotion_weight_memory_weekly_report_latest.json",
    [switch]$BuildOperationalInputs,
    [int]$AtprotoLookbackDays = 0,
    [int]$KpiIntradayStepMinutes = 60,
    [int]$KpiForwardToleranceHours = 6,
    [int]$PromotionWindowSize = 4
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
Set-Location -LiteralPath $workspaceRoot

$builder = Join-Path $workspaceRoot "scripts\build_emotion_weighted_memory_event_v1.py"
$evaluator = Join-Path $workspaceRoot "scripts\evaluate_emotion_weight_memory_weekly_v1.py"
$operInputBuilder = Join-Path $workspaceRoot "scripts\build_operational_emotion_input_v1.py"
$operLabelBuilder = Join-Path $workspaceRoot "scripts\build_operational_emotion_labels_from_kpi_v1.py"
$multiMergeBuilder = Join-Path $workspaceRoot "scripts\build_multisource_emotion_input_v1.py"
$promotionReadinessBuilder = Join-Path $workspaceRoot "scripts\build_emotion_promotion_readiness_v1.py"
$weeklyHistoryJsonl = Join-Path $workspaceRoot "reports\emotion_weight_memory_weekly_history_log.jsonl"
$promotionReadinessJson = Join-Path $workspaceRoot "docs\final\artifacts\emotion_weight_promotion_readiness_latest.json"

if ($BuildOperationalInputs) {
    Write-Host "[emotion-weekly] Build operational sentiment inputs..." -ForegroundColor Cyan
    & py -u $operInputBuilder `
        --atproto-lookback-days $AtprotoLookbackDays `
        --kpi-intraday-step-minutes $KpiIntradayStepMinutes
    if ($LASTEXITCODE -ne 0) {
        throw "build_operational_emotion_input_v1.py failed with exit code $LASTEXITCODE"
    }
    & py -u $operLabelBuilder `
        --kpi-intraday-step-minutes $KpiIntradayStepMinutes `
        --kpi-forward-tolerance-hours $KpiForwardToleranceHours
    if ($LASTEXITCODE -ne 0) {
        throw "build_operational_emotion_labels_from_kpi_v1.py failed with exit code $LASTEXITCODE"
    }
    $primaryInput = "C:\workspace\projects\bitcoin-trading\memory\v2\emotion\operational_sentiment_daily_latest.jsonl"
    $mergedInput = "C:\workspace\projects\bitcoin-trading\memory\v2\emotion\operational_multisource_sentiment_daily_latest.jsonl"
    & py -u $multiMergeBuilder `
        --primary-jsonl $primaryInput `
        --extra-jsonl "C:\workspace\docs\final\hypo_test_sentiment.jsonl" `
        --extra-jsonl "C:\workspace\docs\final\corr_report_001_hypo.jsonl" `
        --out-jsonl $mergedInput
    if ($LASTEXITCODE -ne 0) {
        throw "build_multisource_emotion_input_v1.py failed with exit code $LASTEXITCODE"
    }
    $InputJsonl = $mergedInput
    $LabelsJsonl = "C:\workspace\projects\bitcoin-trading\memory\v2\emotion\operational_emotion_forward_labels_latest.jsonl"
}

if (-not (Test-Path -LiteralPath $builder)) {
    throw "Missing builder script: $builder"
}
if (-not (Test-Path -LiteralPath $evaluator)) {
    throw "Missing evaluator script: $evaluator"
}
if (-not (Test-Path -LiteralPath $InputJsonl)) {
    throw "Input JSONL not found: $InputJsonl"
}

Write-Host "[emotion-weekly] Build emotion-weighted memory events..." -ForegroundColor Cyan
$buildArgs = @("--in-jsonl", $InputJsonl, "--out-jsonl", $OutEventsJsonl)
if ($LabelsJsonl -and (Test-Path -LiteralPath $LabelsJsonl)) {
    $buildArgs += @(
        "--labels-jsonl", $LabelsJsonl,
        "--label-fallback-max-days", "14",
        "--label-fallback-mode", "forward_only"
    )
}
& py -u $builder @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw "build_emotion_weighted_memory_event_v1.py failed with exit code $LASTEXITCODE"
}

Write-Host "[emotion-weekly] Evaluate weekly contribution..." -ForegroundColor Cyan
& py -u $evaluator --events-jsonl $OutEventsJsonl --out-json $OutWeeklyReportJson
if ($LASTEXITCODE -ne 0) {
    throw "evaluate_emotion_weight_memory_weekly_v1.py failed with exit code $LASTEXITCODE"
}

$reportObj = Get-Content -LiteralPath $OutWeeklyReportJson -Raw | ConvertFrom-Json
$historyDir = Split-Path -Parent $weeklyHistoryJsonl
if (-not (Test-Path -LiteralPath $historyDir)) {
    New-Item -ItemType Directory -Path $historyDir | Out-Null
}
$historyEntry = [ordered]@{
    recorded_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    report_path = $OutWeeklyReportJson
    source_gate = $reportObj.source_gate
    gate_hint = $reportObj.gate_hint
    n_total = $reportObj.n_total
    n_usable = $reportObj.n_usable
    coverage_ratio = $reportObj.coverage_ratio
}
Add-Content -LiteralPath $weeklyHistoryJsonl -Value ($historyEntry | ConvertTo-Json -Depth 10 -Compress)

if (Test-Path -LiteralPath $promotionReadinessBuilder) {
    & py -u $promotionReadinessBuilder `
        --history-jsonl $weeklyHistoryJsonl `
        --out-json $promotionReadinessJson `
        --window-size $PromotionWindowSize
    if ($LASTEXITCODE -ne 0) {
        throw "build_emotion_promotion_readiness_v1.py failed with exit code $LASTEXITCODE"
    }
}

$report = $reportObj
$primaryNUsable = [int]($report.source_gate.primary_n_usable)
$minPrimaryGate = [int]($report.source_gate.min_primary_samples_gate)
if ($primaryNUsable -lt $minPrimaryGate) {
    $gap = [int]($report.source_gate.primary_gap_to_gate)
    $webhook = $env:EMOTION_WEIGHT_ALERT_WEBHOOK_URL
    if (-not $webhook) { $webhook = $env:OPS_ALARM_WEBHOOK_URL }
    $msg = "[emotion-weekly] primary gate shortfall: source=$($report.source_gate.primary_source), usable=$primaryNUsable/$minPrimaryGate, gap=$gap, combined=$($report.source_gate.combined_recommended)"
    Write-Warning $msg
    if ($webhook) {
        try {
            $payload = @{ text = $msg } | ConvertTo-Json -Depth 5
            Invoke-RestMethod -Method Post -Uri $webhook -ContentType "application/json" -Body $payload | Out-Null
            Write-Host "[emotion-weekly] Alert sent to webhook." -ForegroundColor Yellow
        } catch {
            Write-Warning "[emotion-weekly] Failed to send webhook alert: $($_.Exception.Message)"
        }
    } else {
        Write-Warning "[emotion-weekly] Alert webhook not configured (EMOTION_WEIGHT_ALERT_WEBHOOK_URL/OPS_ALARM_WEBHOOK_URL)."
    }
}

Write-Host "[emotion-weekly] Done." -ForegroundColor Green
Write-Host "  events: $OutEventsJsonl"
Write-Host "  report: $OutWeeklyReportJson"
exit 0

