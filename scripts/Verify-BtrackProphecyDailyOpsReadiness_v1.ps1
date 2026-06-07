#Requires -Version 5.1
<#
.SYNOPSIS
  Verify Mode B daily prophecy tasks + advisory refresh wiring (readiness only).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Verify-BtrackProphecyDailyOpsReadiness_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$requiredTasks = @(
    "MKM-BTrack-DailyHypothesis-Chain",
    "MKM-Prophecy-Panel-24h-Alerts"
)
$optionalTasks = @(
    "MKM-Prophecy-Daily-Eval-Report",
    "MKM-BTrack-WeeklyOpsSeparation",
    "MKM-BTrack-DualKpi-PanelCompare-Weekly",
    "MKM-Sunday-Automation-LastResult-Audit"
)

$requiredFiles = @(
    "scripts\run_btrack_daily_hypothesis_chain.ps1",
    "scripts\Check-ProphecyPanel24hAlerts.ps1",
    "scripts\Invoke-CheckSundayAutomationLastResult_v1.ps1",
    "scripts\Register-SundayAutomationAuditTask_v1.ps1",
    "scripts\compare_frozen_vs_per_date_combo_panel_v1.py",
    "scripts\Invoke-FrozenVsPerDatePanelCompare_v1.ps1",
    "scripts\run_btrack_kpi_b_shadow_eval_v1.py",
    "scripts\run_btrack_wrong_dir_holdout_v1.py",
    "scripts\build_btrack_prophecy_observation_mode_status_v1.py",
    "scripts\build_bbs_ms_hybrid_today_shadow_digest_v1.py",
    "scripts\run_btrack_model_swap_harness_v1.py",
    "reports\btrack_advisory_bear_trap_manifest_v1_latest.json",
    "docs\final\artifacts\btrack_lens_ensemble_v1.json"
)

$fail = $false
Write-Host "=== B-track prophecy daily ops readiness ===" -ForegroundColor Cyan

foreach ($rel in $requiredFiles) {
    $p = Join-Path $WorkspaceRoot $rel
    if (Test-Path -LiteralPath $p) {
        Write-Host "[OK] $rel" -ForegroundColor Green
    } else {
        Write-Host "[MISS] $rel" -ForegroundColor Red
        $fail = $true
    }
}

foreach ($tn in $requiredTasks) {
    $t = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if (-not $t) {
        Write-Host "[MISS] Task $tn" -ForegroundColor Red
        $fail = $true
        continue
    }
    $i = Get-ScheduledTaskInfo -TaskName $tn
    $state = $t.State
    Write-Host "[OK] Task $tn State=$state Next=$($i.NextRunTime)" -ForegroundColor Green
}

foreach ($tn in $optionalTasks) {
    $t = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if ($t) {
        $i = Get-ScheduledTaskInfo -TaskName $tn
        Write-Host "[OK] Optional $tn Next=$($i.NextRunTime)" -ForegroundColor DarkGreen
    } else {
        Write-Host "[--] Optional task not registered: $tn" -ForegroundColor DarkYellow
    }
}

$chain = Get-Content -LiteralPath (Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1") -Raw
if ($chain -match "advisory-sweep") {
    Write-Host "[OK] Chain includes advisory-sweep" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Chain missing advisory-sweep" -ForegroundColor Red
    $fail = $true
}

$panel = Get-Content -LiteralPath (Join-Path $WorkspaceRoot "scripts\Check-ProphecyPanel24hAlerts.ps1") -Raw
if ($panel -match "advisory-sweep") {
    Write-Host "[OK] Panel includes advisory-sweep refresh" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Panel missing advisory-sweep" -ForegroundColor Red
    $fail = $true
}

if ($chain -match "run_btrack_model_swap_harness_v1") {
    Write-Host "[OK] Chain includes model-swap harness (30d)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Chain missing model-swap harness" -ForegroundColor Red
    $fail = $true
}

if ($panel -match "compare_frozen_vs_per_date_combo_panel_v1") {
    Write-Host "[OK] Panel includes Dual-KPI compare refresh" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Panel missing Dual-KPI compare" -ForegroundColor Red
    $fail = $true
}

if ($chain -match "run_btrack_kpi_b_shadow_eval_v1") {
    Write-Host "[OK] Chain includes KPI-B shadow eval (parallel headline)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Chain missing KPI-B shadow eval" -ForegroundColor Red
    $fail = $true
}

if ($panel -match "kpi_b_operational_headline") {
    Write-Host "[OK] Panel includes KPI-B operational ALERT_1 policy" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Panel missing KPI-B operational ALERT_1 policy" -ForegroundColor Red
    $fail = $true
}

$approvalPath = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_dual_kpi_headline_human_approval_v1_latest.json"
if (Test-Path -LiteralPath $approvalPath) {
    try {
        $ap = Get-Content -LiteralPath $approvalPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]$ap.decision -eq "APPROVED_KPI_B_OPERATIONAL_HEADLINE") {
            Write-Host "[OK] KPI-B headline human approval on disk" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Approval file present but decision=$($ap.decision)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARN] Could not parse approval JSON" -ForegroundColor Yellow
    }
} else {
    Write-Host "[--] KPI-B approval file absent (frozen ALERT_1 coin-flip only)" -ForegroundColor DarkYellow
}

if ($fail) { exit 1 }
Write-Host "ALL OK: B-track prophecy daily ops readiness" -ForegroundColor Cyan
exit 0
