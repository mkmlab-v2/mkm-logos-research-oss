param(
  [string]$WorkspaceRoot = "C:\workspace",
  [double]$NormalMinPassRate = 0.95,
  [double]$NormalCriticalPassRate = 0.85,
  [double]$DrillMinPassRate = 1.1,
  [double]$DrillCriticalPassRate = 1.05
)

$ErrorActionPreference = "Stop"

$dailyGate = Join-Path $WorkspaceRoot "scripts\run_xai_contract_daily_gate_v1.ps1"
$weekly = Join-Path $WorkspaceRoot "scripts\run_xai_contract_weekly_reporting_v1.ps1"
$summaryPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_monthly_governance_drill_latest.json"

$steps = @()
function Add-Step([string]$step, [bool]$ok, [string]$detail) {
  $script:steps += [pscustomobject]@{
    step = $step
    ok = $ok
    detail = $detail
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  }
}

try {
  Set-Location -LiteralPath $WorkspaceRoot
  if (-not (Test-Path -LiteralPath $dailyGate)) { throw "Missing script: $dailyGate" }
  if (-not (Test-Path -LiteralPath $weekly)) { throw "Missing script: $weekly" }

  # Step 1) Force a critical HOLD
  & powershell -NoProfile -ExecutionPolicy Bypass -File $dailyGate -WorkspaceRoot $WorkspaceRoot -MinPassRate $DrillMinPassRate -CriticalPassRate $DrillCriticalPassRate -BootstrapIfMissing
  if ($LASTEXITCODE -ne 0) { throw "drill_hold_run failed exit=$LASTEXITCODE" }
  Add-Step "drill_hold_run" $true "forced HOLD with strict thresholds"

  $holdSummary = Get-Content -Raw -LiteralPath (Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_daily_gate_summary_latest.json") | ConvertFrom-Json
  $holdOk = ([string]$holdSummary.status -eq "HOLD")
  Add-Step "verify_hold_detected" $holdOk "status=$($holdSummary.status) severity=$($holdSummary.severity)"
  if (-not $holdOk) { throw "expected HOLD during drill" }

  # Step 2) Build weekly + queue during degraded state
  & powershell -NoProfile -ExecutionPolicy Bypass -File $weekly -WorkspaceRoot $WorkspaceRoot -WindowDays 7 -DefaultOwner "xai-ops" -DueDays 2
  if ($LASTEXITCODE -ne 0) { throw "weekly_reporting_during_drill failed exit=$LASTEXITCODE" }
  Add-Step "weekly_reporting_during_drill" $true "weekly report + action queue generated"

  # Step 3) Recover to PASS
  & powershell -NoProfile -ExecutionPolicy Bypass -File $dailyGate -WorkspaceRoot $WorkspaceRoot -MinPassRate $NormalMinPassRate -CriticalPassRate $NormalCriticalPassRate -BootstrapIfMissing
  if ($LASTEXITCODE -ne 0) { throw "drill_recovery_run failed exit=$LASTEXITCODE" }
  Add-Step "drill_recovery_run" $true "restored normal thresholds"

  $passSummary = Get-Content -Raw -LiteralPath (Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_daily_gate_summary_latest.json") | ConvertFrom-Json
  $passOk = ([string]$passSummary.status -eq "PASS")
  Add-Step "verify_pass_recovered" $passOk "status=$($passSummary.status) severity=$($passSummary.severity)"
  if (-not $passOk) { throw "expected PASS after recovery" }

  $out = [pscustomobject]@{
    schema = "xai_contract_monthly_governance_drill_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "PASS"
    normal_thresholds = [pscustomobject]@{
      min_pass_rate = $NormalMinPassRate
      critical_pass_rate = $NormalCriticalPassRate
    }
    drill_thresholds = [pscustomobject]@{
      min_pass_rate = $DrillMinPassRate
      critical_pass_rate = $DrillCriticalPassRate
    }
    steps = $steps
  }
  $out | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
  Write-Host "[ok] monthly governance drill summary -> $summaryPath"
  exit 0
}
catch {
  Add-Step "pipeline_exception" $false $_.Exception.Message
  $out = [pscustomobject]@{
    schema = "xai_contract_monthly_governance_drill_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "FAIL"
    error = $_.Exception.Message
    steps = $steps
  }
  $out | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
  Write-Host "[err] monthly governance drill failed -> $summaryPath"
  exit 1
}
