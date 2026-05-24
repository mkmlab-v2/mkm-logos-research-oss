#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 원클릭 자동: 일상(envelope+deploy+probe+CF+summary) + 주간 롤업. 선택 -FullParallel.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$FullParallel,
    [switch]$SkipLivePatrol
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$reportPath = Join-Path $WorkspaceRoot "reports\op30_auto_run_latest.json"
$failed = @()
$steps = [ordered]@{}

# CF jemaai rulesets scope gate (recurrence counter; no apply spam)
$cfRecurrencePath = Join-Path $WorkspaceRoot "reports\cloudflare_jemaai_scope_recurrence_v1_latest.json"
$cfBlocked = $false
$cfBlocked7d = 0
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
& $py scripts/record_cloudflare_jemaai_scope_recurrence_v1.py 2>&1 | Out-Null
if (Test-Path $cfRecurrencePath) {
    $cfGate = Get-Content -LiteralPath $cfRecurrencePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $cfBlocked = -not $cfGate.automation_ready
    if ($cfGate.recurrence) { $cfBlocked7d = [int]$cfGate.recurrence.'blocked_last_7d' }
    if ($cfBlocked) {
        Write-Host "[CF-GATE] jemaai rulesets NOT automation_ready (verify OK + rulesets 403 = scope). blocked_last_7d=$cfBlocked7d — skip API apply; fix: WAF+Cache Rules Edit on jemaai.cloud. SSOT: docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md" -ForegroundColor Yellow
    }
}
$steps["cf_jemaai_scope_gate_ok"] = -not $cfBlocked

Write-Host "==> O-P30 Auto: Phase2 daily" -ForegroundColor Cyan
$phase2Args = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $WorkspaceRoot "scripts\Invoke-Op30Phase2Daily_v1.ps1"),
    "-DeployAssets"
)
if (-not $SkipLivePatrol) { $phase2Args += "-IncludeLivePatrol" }
powershell @phase2Args
$steps["phase2_daily"] = ($LASTEXITCODE -eq 0)
if (-not $steps["phase2_daily"]) { $failed += "phase2_daily" }

Write-Host "==> O-P30 Auto: weekly rollup" -ForegroundColor Cyan
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
& $py scripts/build_magic_orb_open_beta_weekly_rollup_v1.py
$steps["weekly_rollup"] = ($LASTEXITCODE -eq 0)
if (-not $steps["weekly_rollup"]) { $failed += "weekly_rollup" }

if ($FullParallel) {
    Write-Host "==> O-P30 Auto: Phase3 parallel (heavy)" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-Op30Phase3Parallel_v1.ps1") -SkipLivePatrol
    $steps["phase3_parallel"] = ($LASTEXITCODE -eq 0)
    if (-not $steps["phase3_parallel"]) { $failed += "phase3_parallel" }
}

$summaryPath = Join-Path $WorkspaceRoot "reports\magic_orb_open_beta_traffic_summary_latest.json"
$hist = 0
$streak = $null
if (Test-Path $summaryPath) {
    $s = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $hist = $s.history_entries_total
    $streak = $s.streak_all_ok_from_latest
}

$cfGateNote = $null
if (Test-Path $cfRecurrencePath) {
    $cfGateNote = Get-Content -LiteralPath $cfRecurrencePath -Raw -Encoding UTF8 | ConvertFrom-Json
}
[ordered]@{
    schema = "op30_auto_run_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_steps = @($failed)
    steps = $steps
    probe_history_entries = $hist
    streak_all_ok = $streak
    full_parallel = $FullParallel.IsPresent
    cf_jemaai_scope_blocked = $cfBlocked
    cf_jemaai_blocked_last_7d = $cfBlocked7d
    cf_jemaai_scope_recurrence_json = $(if ($cfGateNote) { "reports/cloudflare_jemaai_scope_recurrence_v1_latest.json" } else { $null })
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "Wrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
