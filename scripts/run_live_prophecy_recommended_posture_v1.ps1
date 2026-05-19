# Apply triage recommendation: shadow prophecy + separate live ops (no auto-promote, no live disable).
# Does NOT: EnableBtcPromotionAutoExecute, promote operational headline, apply_prophecy_live_enable, PM2 restart.
param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [switch]$SkipDailyEval,
  [switch]$SkipDailyChain,
  [switch]$SkipMarketDataRefresh
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$logPath = Join-Path $WorkspaceRoot "reports\live_prophecy_recommended_posture_log.jsonl"
$appliedPath = Join-Path $WorkspaceRoot "reports\live_prophecy_recommended_posture_applied_v1_latest.json"
$started = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$steps = @()

function Restore-KpiBOperationalHeadlineIfApproved {
  $approval = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_dual_kpi_headline_human_approval_v1_latest.json"
  if (-not (Test-Path -LiteralPath $approval)) { return $false }
  $ap = Get-Content -LiteralPath $approval -Raw -Encoding UTF8 | ConvertFrom-Json
  if ([string]$ap.decision -ne "APPROVED_KPI_B_OPERATIONAL_HEADLINE") { return $false }
  $evalSrc = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_kpi_b_shadow_30d_v1_latest.json"
  $scoreSrc = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_kpi_b_shadow_30d_v1_latest.json"
  if (-not ((Test-Path -LiteralPath $evalSrc) -and (Test-Path -LiteralPath $scoreSrc))) {
    Write-Warning "KPI-B 30d shadow artifacts missing; skip headline restore."
    return $false
  }
  Copy-Item -LiteralPath $evalSrc -Destination (Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_hit_rate_eval_latest.json") -Force
  Copy-Item -LiteralPath $scoreSrc -Destination (Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_prophecy_score_latest.json") -Force
  Write-Host "Restored KPI-B operational headline from 30d shadow artifacts." -ForegroundColor Cyan
  return $true
}

function Add-Step($name, $exitCode, $note, [switch]$AllowFail) {
  $script:steps += [ordered]@{
    step = $name
    exit_code = $exitCode
    ok = ($exitCode -eq 0)
    note = $note
  }
  if ($exitCode -ne 0 -and -not $AllowFail) { throw "${name} exit ${exitCode}" }
  if ($exitCode -ne 0) { Write-Warning "${name} exit ${exitCode}; continuing." }
}

Write-Host "==> build_live_vs_prophecy_triage_v1.py" -ForegroundColor Cyan
py scripts/build_live_vs_prophecy_triage_v1.py
Add-Step "triage" $LASTEXITCODE "refresh SSOT"

Write-Host "==> run_btrack_frozen30d_parallel_bundle_v10.py (BBS+MS shadow pack)" -ForegroundColor Cyan
py scripts/run_btrack_frozen30d_parallel_bundle_v10.py
Add-Step "frozen30d_bundle_v10" $LASTEXITCODE "shadow lane + observation"

if (-not $SkipDailyEval) {
  Write-Host "==> run_daily_prophecy_eval_and_report.ps1 (shadow panel; no promotion)" -ForegroundColor Cyan
  $btcCsv = Join-Path $WorkspaceRoot "research\market_data\btc_daily_external_yf.csv"
  $evalArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", "scripts\run_daily_prophecy_eval_and_report.ps1",
    "-IncludeShadowPanelEval",
    "-SkipTrinityEvolution",
    "-SkipRiskProfileSync",
    "-OperationModeBShadow",
    "-BtcCsvPath", $btcCsv
  )
  & powershell @evalArgs
  Add-Step "daily_prophecy_eval_shadow" $LASTEXITCODE "measurement only"
  if (Restore-KpiBOperationalHeadlineIfApproved) {
    Add-Step "restore_kpi_b_headline" 0 "daily 1-row eval must not replace approved KPI-B headline"
    py scripts/evaluate_prophecy_runtime_health_v1.py --operation-mode-b-shadow
    Add-Step "runtime_health_mode_b" $LASTEXITCODE "post-restore health"
    py scripts/build_live_vs_prophecy_triage_v1.py
    Add-Step "triage_post_restore" $LASTEXITCODE "refresh after KPI-B restore"
  }
}

if (-not $SkipDailyChain) {
  Write-Host "==> run_btrack_daily_hypothesis_chain.ps1 (observation; no KPI-B promote)" -ForegroundColor Cyan
  $chainScript = Join-Path $WorkspaceRoot "scripts\run_btrack_daily_hypothesis_chain.ps1"
  $chainParams = @{
    WorkspaceRoot = $WorkspaceRoot
    SkipKpiBShadowEval = $true
    SkipKpiBOperationalHeadlinePromote = $true
    SkipModelSwapHarness = $true
    SkipAdvisoryBearTrapSweep = $true
    SkipPanel24hAlertsCheck = $true
  }
  if ($SkipMarketDataRefresh) { $chainParams.SkipMarketDataRefresh = $true }
  & $chainScript @chainParams
  Add-Step "btrack_daily_chain" $LASTEXITCODE "S1_SHADOW path; KPI-B promote skipped" -AllowFail
}

Write-Host "==> build_btrack_daily_p15_shadow_status_v1.py" -ForegroundColor Cyan
py scripts/build_btrack_daily_p15_shadow_status_v1.py
Add-Step "p15_shadow_status" $LASTEXITCODE ""

Write-Host "==> build_bbs_ms_hybrid_today_shadow_digest_v1.py" -ForegroundColor Cyan
py scripts/build_bbs_ms_hybrid_today_shadow_digest_v1.py
Add-Step "bbs_today_digest" $LASTEXITCODE ""

Write-Host "==> apply_live_fee_guard_recommended_posture_v1.py (cap trades/day; no prophecy route)" -ForegroundColor Cyan
py scripts/apply_live_fee_guard_recommended_posture_v1.py
Add-Step "live_fee_guard" $LASTEXITCODE "max_trades_per_day cap for commission bleed"

$healthScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\check_live_trading_health.ps1"
if (Test-Path -LiteralPath $healthScript) {
  Write-Host "==> check_live_trading_health.ps1" -ForegroundColor Cyan
  & $healthScript
  Add-Step "live_health" $LASTEXITCODE "daemon + 24h fills snapshot"
}

$triage = Get-Content "reports\live_vs_prophecy_triage_v1_latest.json" -Raw | ConvertFrom-Json
$digest = Get-Content "reports\btrack_bbs_ms_hybrid_today_shadow_digest_v1_latest.json" -Raw | ConvertFrom-Json
$feeGuardMaxTrades = $null
if (Test-Path -LiteralPath "reports\live_fee_guard_applied_v1_latest.json") {
  $fg = Get-Content "reports\live_fee_guard_applied_v1_latest.json" -Raw | ConvertFrom-Json
  $feeGuardMaxTrades = $fg.after.max_trades_per_day
}

$applied = @{
  schema = "live_prophecy_recommended_posture_applied_v1"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  research_only = $true
  posture = "shadow_prophecy_only"
  triage_path = "reports/live_vs_prophecy_triage_v1_latest.json"
  primary_axis = $triage.primary_axis
  live_mutations = @{
    trading_disabled = $false
    prophecy_routed_orders = $false
    operational_headline_promoted = $false
    risk_profile_synced = $false
    fee_guard_max_trades_per_day = $feeGuardMaxTrades
  }
  operator_today = @{
    eval_date = $digest.eval_date
    headline_direction = $digest.headline_operational.predicted_direction
    shadow_direction = $digest.shadow_candidate.today_row.bbs_ms_hybrid
    agrees = $digest.shadow_candidate.agrees_with_headline
  }
  live_24h_note = $triage.live_24h
  steps = $steps
  refresh = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_live_prophecy_recommended_posture_v1.ps1"
}
$applied | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $appliedPath -Encoding utf8

$logLine = (@{
  ts_utc = $applied.generated_at_utc
  posture = "shadow_prophecy_only"
  eval_date = $digest.eval_date
  headline = $digest.headline_operational.predicted_direction
  shadow = $digest.shadow_candidate.today_row.bbs_ms_hybrid
} | ConvertTo-Json -Compress)
Add-Content -LiteralPath $logPath -Value $logLine -Encoding utf8

Write-Host "WROTE: $appliedPath" -ForegroundColor Green
Write-Host "DONE recommended posture (shadow only; live unchanged)" -ForegroundColor Green
