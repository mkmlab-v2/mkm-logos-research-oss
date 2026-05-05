param(
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$Windows = "30,60,120",
  [int]$WalkforwardStartDays = 30,
  [int]$WalkforwardStopDays = 210,
  [int]$WalkforwardStepDays = 30
)

$ErrorActionPreference = "Stop"

$summaryPath = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_bridge_size_daily_gate_summary_latest.json"
$alertPath = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_bridge_size_daily_gate_alert_latest.json"
$holdoutPath = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_bridge_size_holdout_eval_latest.json"
$walkforwardPath = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_bridge_size_walkforward_eval_latest.json"
$gatePath = Join-Path $WorkspaceRoot "docs\final\artifacts\compression_bridge_size_promotion_gate_latest.json"

$script:steps = @()
function Add-Step([string]$name, [bool]$ok, [string]$detail) {
  $script:steps += [pscustomobject]@{
    step = $name
    ok = $ok
    detail = $detail
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  }
}

try {
  Set-Location -LiteralPath $WorkspaceRoot

  py (Join-Path $WorkspaceRoot "scripts\run_compression_bridge_size_holdout_eval_v1.py") `
    --windows $Windows `
    --output $holdoutPath
  if ($LASTEXITCODE -ne 0) { throw "run_compression_bridge_size_holdout_eval_v1.py exit=$LASTEXITCODE" }
  Add-Step "holdout_eval" $true "windows=$Windows"

  py (Join-Path $WorkspaceRoot "scripts\run_compression_bridge_size_walkforward_eval_v1.py") `
    --start-days $WalkforwardStartDays `
    --stop-days $WalkforwardStopDays `
    --step-days $WalkforwardStepDays `
    --output $walkforwardPath
  if ($LASTEXITCODE -ne 0) { throw "run_compression_bridge_size_walkforward_eval_v1.py exit=$LASTEXITCODE" }
  Add-Step "walkforward_eval" $true "range=${WalkforwardStartDays}-${WalkforwardStopDays}/${WalkforwardStepDays}"

  py (Join-Path $WorkspaceRoot "scripts\check_compression_bridge_size_promotion_gate_v1.py") `
    --holdout-eval $holdoutPath `
    --walkforward-eval $walkforwardPath `
    --output $gatePath
  if ($LASTEXITCODE -ne 0) { throw "check_compression_bridge_size_promotion_gate_v1.py exit=$LASTEXITCODE" }
  Add-Step "promotion_gate" $true "gate_json_written"

  $gate = Get-Content -Raw -LiteralPath $gatePath | ConvertFrom-Json
  $decision = [string]$gate.decision
  $status = if ($decision -eq "GO_SIZE_LANE_PROMOTION_CONFIRMED") { "PASS" } else { "HOLD" }

  $summary = [pscustomobject]@{
    schema = "compression_bridge_size_daily_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    windows = $Windows
    walkforward = [pscustomobject]@{
      start_days = $WalkforwardStartDays
      stop_days = $WalkforwardStopDays
      step_days = $WalkforwardStepDays
    }
    steps = $script:steps
    decision = $decision
    status = $status
    holdout_eval_path = $holdoutPath
    walkforward_eval_path = $walkforwardPath
    gate_path = $gatePath
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
  Write-Host "[ok] daily gate summary -> $summaryPath"

  if ($status -ne "PASS") {
    $alert = [pscustomobject]@{
      schema = "compression_bridge_size_daily_gate_alert_v1"
      generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
      severity = "warning"
      title = "Compression bridge size daily gate is HOLD"
      message = "Daily gate decision is $decision"
      summary_path = $summaryPath
      gate_path = $gatePath
    }
    $alert | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $alertPath -Encoding UTF8
    Write-Host "[warn] HOLD alert -> $alertPath"
  }

  exit 0
}
catch {
  Add-Step "pipeline_exception" $false $_.Exception.Message
  $summary = [pscustomobject]@{
    schema = "compression_bridge_size_daily_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    windows = $Windows
    walkforward = [pscustomobject]@{
      start_days = $WalkforwardStartDays
      stop_days = $WalkforwardStopDays
      step_days = $WalkforwardStepDays
    }
    steps = $script:steps
    status = "FAIL"
    error = $_.Exception.Message
    holdout_eval_path = $holdoutPath
    walkforward_eval_path = $walkforwardPath
    gate_path = $gatePath
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

  $alert = [pscustomobject]@{
    schema = "compression_bridge_size_daily_gate_alert_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    severity = "critical"
    title = "Compression bridge size daily gate failed"
    message = $_.Exception.Message
    summary_path = $summaryPath
  }
  $alert | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $alertPath -Encoding UTF8
  Write-Host "[err] failed; alert -> $alertPath"
  exit 1
}

