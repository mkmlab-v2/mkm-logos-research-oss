[CmdletBinding()]
param(
  [string]$WorkspaceRoot = "",
  [string]$Symbol = "BTCUSDT",
  [double]$TpOffsetPct = 0.8,
  [double]$SlOffsetPct = 1.0,
  [int]$PositionSwitchCooldownMinutes = 2
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  } else {
    $WorkspaceRoot = (Get-Location).Path
  }
}

Set-Location -LiteralPath $WorkspaceRoot

$policyPath = Join-Path $WorkspaceRoot "reports\trading_guardian_policy_latest.json"
if (Test-Path -LiteralPath $policyPath) {
  try {
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    if ($policy -and $policy.protective_guard) {
      if ($policy.protective_guard.symbol) { $Symbol = "$($policy.protective_guard.symbol)" }
      if ($null -ne $policy.protective_guard.tp_offset_pct) { $TpOffsetPct = [double]$policy.protective_guard.tp_offset_pct }
      if ($null -ne $policy.protective_guard.sl_offset_pct) { $SlOffsetPct = [double]$policy.protective_guard.sl_offset_pct }
      if ($null -ne $policy.protective_guard.position_switch_cooldown_minutes) { $PositionSwitchCooldownMinutes = [int]$policy.protective_guard.position_switch_cooldown_minutes }
    }
  } catch {
    Write-Host "[warn] trading_guardian_policy parse failed, using runtime args/defaults"
  }
}

$check = Join-Path $WorkspaceRoot "projects\bitcoin-trading\scripts\check_binance_usdm_protective_coverage_v1.py"
$alert = Join-Path $WorkspaceRoot "projects\bitcoin-trading\scripts\alert_protective_coverage_uncovered_v1.py"
$repair = Join-Path $WorkspaceRoot "projects\bitcoin-trading\scripts\execute_binance_usdm_protective_orders_v1.py"
$coveragePath = Join-Path $WorkspaceRoot "reports\binance_usdm_single_order\protective_order_coverage_latest.json"
$statePath = Join-Path $WorkspaceRoot "reports\binance_usdm_single_order\protective_guard_state_latest.json"
if (-not (Test-Path -LiteralPath $check)) { throw "Missing script: $check" }
if (-not (Test-Path -LiteralPath $alert)) { throw "Missing script: $alert" }
if (-not (Test-Path -LiteralPath $repair)) { throw "Missing script: $repair" }

py $check --symbol $Symbol --mainnet --strict-exit --out "reports/binance_usdm_single_order/protective_order_coverage_latest.json"
$checkExit = $LASTEXITCODE

if ($checkExit -ne 0) {
  Write-Host "[warn] uncovered detected - attempting auto-repair (symbol=$Symbol)"
  py $repair --symbol $Symbol --tp-offset-pct $TpOffsetPct --sl-offset-pct $SlOffsetPct --live --mainnet
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[warn] auto-repair order placement failed (symbol=$Symbol)"
  }

  py $check --symbol $Symbol --mainnet --strict-exit --out "reports/binance_usdm_single_order/protective_order_coverage_latest.json"
  $checkExit = $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $coveragePath)) {
  throw "Missing coverage output: $coveragePath"
}
$coverage = Get-Content -LiteralPath $coveragePath -Raw | ConvertFrom-Json
$currentSide = ""
if ($coverage.position -and $coverage.position.side) {
  $currentSide = "$($coverage.position.side)".ToUpperInvariant()
}
$nowUtc = [DateTime]::UtcNow

$state = [ordered]@{
  schema = "protective_guard_state_v1"
  updated_at_utc = $nowUtc.ToString("o")
  symbol = $Symbol
  last_position_side = $currentSide
  last_side_changed_at_utc = $null
}
if (Test-Path -LiteralPath $statePath) {
  try {
    $prev = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($prev) {
      $state.last_position_side = if ($prev.last_position_side) { "$($prev.last_position_side)" } else { $currentSide }
      $state.last_side_changed_at_utc = if ($prev.last_side_changed_at_utc) { "$($prev.last_side_changed_at_utc)" } else { $null }
    }
  } catch {
    # Ignore broken state and rebuild from current snapshot.
  }
}

$sideChanged = $false
if (-not [string]::IsNullOrWhiteSpace($currentSide) -and $state.last_position_side -ne $currentSide) {
  $sideChanged = $true
  $state.last_position_side = $currentSide
  $state.last_side_changed_at_utc = $nowUtc.ToString("o")
}
if ([string]::IsNullOrWhiteSpace($state.last_side_changed_at_utc) -and -not [string]::IsNullOrWhiteSpace($currentSide)) {
  $state.last_side_changed_at_utc = $nowUtc.ToString("o")
}
$state.updated_at_utc = $nowUtc.ToString("o")
$state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding UTF8

$skipAlertByCooldown = $false
if ($checkExit -ne 0 -and $state.last_side_changed_at_utc) {
  try {
    $changedAt = [DateTime]::Parse("$($state.last_side_changed_at_utc)").ToUniversalTime()
    $elapsedMin = ($nowUtc - $changedAt).TotalMinutes
    if ($elapsedMin -lt [Math]::Max(0, $PositionSwitchCooldownMinutes)) {
      $skipAlertByCooldown = $true
      Write-Host "[warn] uncovered but cooldown active after side switch (elapsed_min=$([Math]::Round($elapsedMin,2)), cooldown_min=$PositionSwitchCooldownMinutes, side=$currentSide)"
    }
  } catch {
    # If timestamp parse fails, do not skip alerts.
  }
}

if (-not $skipAlertByCooldown) {
  py $alert
  if ($LASTEXITCODE -ne 0) {
    throw "alert_protective_coverage_uncovered_v1.py exit $LASTEXITCODE"
  }
} else {
  Write-Host "[info] alert skipped due to position-switch cooldown (symbol=$Symbol)"
}

if ($checkExit -eq 0) {
  Write-Host "[ok] protective coverage: covered (symbol=$Symbol)"
} else {
  if ($skipAlertByCooldown) {
    Write-Host "[warn] protective coverage: uncovered after auto-repair (symbol=$Symbol, alert deferred by cooldown)"
  } else {
    Write-Host "[warn] protective coverage: uncovered after auto-repair (symbol=$Symbol, alert sent)"
  }
}
exit 0
