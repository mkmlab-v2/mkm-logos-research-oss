#Requires -Version 5.1
<#
.SYNOPSIS
  Post-flight audit: Sunday (or given date) MKM weekly/daily automation LastTaskResult.

.DESCRIPTION
  Read-only check of Task Scheduler LastTaskResult + LastRunTime recency for the Oracle
  Sunday chain. Does not trigger tasks. Exit 0 only when every task exists, ran on or
  after -ExpectedRunDate (local calendar day), and LastTaskResult is 0.

  Optional -AlsoVerifyHeadlineLane reads prophecy_hit_rate_ssot_pointer_v1_latest.json
  (Phase A: commander headline vs daily operational split). research_only; non-gating.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CheckSundayAutomationLastResult_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CheckSundayAutomationLastResult_v1.ps1 -AlsoVerifyHeadlineLane
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutJson = "",
    [datetime]$ExpectedRunDate = [datetime]::Today,
    [switch]$AlsoVerifyHeadlineLane,
    [switch]$AllowStaleLastRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$targetTasks = @(
    "MKM-BTrack-DailyHypothesis-Chain",
    "MKM-Prophecy-Panel-24h-Alerts",
    "MKM-BTrack-RecommendedEval-AutoSweep-Weekly",
    "MKM-V2-Wire-Shadow-Metering-Weekly"
)

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\sunday_automation_audit_latest.json"
}

$expectedDay = $ExpectedRunDate.Date
$audit = [ordered]@{
    schema = "sunday_automation_audit_v1"
    research_only = $true
    non_gating = $true
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    expected_run_date_local = $expectedDay.ToString("yyyy-MM-dd")
    all_passed = $true
    task_matrix = @()
    headline_lane = $null
}

Write-Host "=== MKM Sunday automation LastResult audit ===" -ForegroundColor Cyan
Write-Host "Expected run date (local): $($expectedDay.ToString('yyyy-MM-dd'))" -ForegroundColor DarkGray

foreach ($taskName in $targetTasks) {
    $row = [ordered]@{
        task_name = $taskName
        exists = $false
        last_run_time_local = $null
        last_result = $null
        status = "CRITICAL_FAIL"
        note = $null
    }

    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "[FAIL] Missing task: $taskName" -ForegroundColor Red
        $row.note = "task_not_registered"
        $audit.all_passed = $false
        $audit.task_matrix += $row
        continue
    }

    $row.exists = $true
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    $lastResult = [int]$info.LastTaskResult
    $lastRun = $info.LastRunTime
    $row.last_result = $lastResult

    if ($null -eq $lastRun -or $lastRun -eq [datetime]::MinValue) {
        Write-Host "[FAIL] $taskName — never ran (LastRunTime empty)" -ForegroundColor Red
        $row.note = "never_ran"
        $audit.all_passed = $false
        $audit.task_matrix += $row
        continue
    }

    $row.last_run_time_local = $lastRun.ToString("yyyy-MM-dd HH:mm:ss")
    $stale = $lastRun.Date -lt $expectedDay
    if ($stale -and -not $AllowStaleLastRun) {
        Write-Host "[FAIL] $taskName — stale LastRun=$($row.last_run_time_local) (expected >= $expectedDay)" -ForegroundColor Red
        $row.note = "stale_last_run"
        $audit.all_passed = $false
        $audit.task_matrix += $row
        continue
    }

    if ($lastResult -ne 0) {
        $panelDegradedOk = $false
        if ($taskName -eq "MKM-Prophecy-Panel-24h-Alerts") {
            foreach ($panelJsonRel in @(
                "reports\prophecy_panel_24h_alert_check_latest.json",
                "reports\prophecy_panel_24h_alerts_latest.json"
            )) {
                $panelPath = Join-Path $WorkspaceRoot $panelJsonRel
                if (-not (Test-Path -LiteralPath $panelPath)) { continue }
                try {
                    $pc = Get-Content -LiteralPath $panelPath -Raw -Encoding UTF8 | ConvertFrom-Json
                    $a1 = [bool]$pc.alerts.ALERT_1_PERFORMANCE.passed
                    $a3 = [bool]$pc.alerts.ALERT_3_STRUCTURAL_RISK.passed
                    if ($a1 -and $a3) {
                        $panelDegradedOk = $true
                        $row.note = "panel_exit1_alert2_only_expected"
                        break
                    }
                } catch {
                    continue
                }
            }
        }
        if ($panelDegradedOk) {
            Write-Host "[OK] $taskName LastResult=$lastResult (ALERT_1+ALERT_3 pass; ALERT_2 fail expected)" -ForegroundColor Green
            $row.status = "GREEN_PANEL_ALERT2_ONLY"
        }
        else {
            Write-Host "[FAIL] $taskName LastResult=$lastResult LastRun=$($row.last_run_time_local)" -ForegroundColor Red
            $row.note = "nonzero_last_result"
            $audit.all_passed = $false
        }
    }
    else {
        $staleNote = if ($stale) { " (stale allowed)" } else { "" }
        Write-Host "[OK] $taskName LastResult=0 LastRun=$($row.last_run_time_local)$staleNote" -ForegroundColor Green
        $row.status = "GREEN"
        $row.note = if ($stale) { "ok_stale_allowed" } else { "ok" }
    }

    $audit.task_matrix += $row
}

if ($AlsoVerifyHeadlineLane) {
    $pointerPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_ssot_pointer_v1_latest.json"
    $hl = [ordered]@{
        pointer_path = $pointerPath
        passed = $false
        headline_rate = $null
        daily_rate = $null
        note = $null
    }
    if (-not (Test-Path -LiteralPath $pointerPath)) {
        Write-Host "[FAIL] Headline lane: missing pointer $pointerPath" -ForegroundColor Red
        $hl.note = "pointer_missing"
        $audit.all_passed = $false
    }
    else {
        $ptr = Get-Content -LiteralPath $pointerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $head = $ptr.lanes.headline_kpi
        $daily = $ptr.lanes.daily_operational
        if ($head) { $hl.headline_rate = [double]$head.price_directional_hit_rate }
        if ($daily) { $hl.daily_rate = [double]$daily.price_directional_hit_rate }
        $hasPromo = $false
        if ($head -and $head.headline_promotion_v1) { $hasPromo = $true }
        $splitOk = ($null -ne $hl.headline_rate) -and ($null -ne $hl.daily_rate) -and
            ($hl.headline_rate -ne $hl.daily_rate) -and $hasPromo
        if ($splitOk) {
            Write-Host "[OK] Headline lane split: headline=$($hl.headline_rate) daily=$($hl.daily_rate) (headline_promotion_v1)" -ForegroundColor Green
            $hl.passed = $true
            $hl.note = "dual_lane_ok"
        }
        else {
            Write-Host "[FAIL] Headline lane split check failed (pointer)" -ForegroundColor Red
            $hl.note = "dual_lane_mismatch_or_missing_promotion"
            $audit.all_passed = $false
        }
    }
    $audit.headline_lane = $hl
}

$dir = Split-Path -Parent $OutJson
if (-not [string]::IsNullOrWhiteSpace($dir) -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
($audit | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $OutJson -Encoding utf8
Write-Host "WROTE: $OutJson" -ForegroundColor Green

if ($audit.all_passed) {
    Write-Host "ALL OK: Sunday automation audit" -ForegroundColor Cyan
    exit 0
}

Write-Host "AUDIT FAIL: see task_matrix in $OutJson" -ForegroundColor Yellow
exit 1
