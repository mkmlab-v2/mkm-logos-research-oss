param(
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$MetricsJsonPath = "",
  [string]$PolicyJsonPath = "",
  [string]$OutputJsonPath = "",
  [string]$SummaryOutPath = "",
  [string]$LogJsonlPath = "",
  [string]$AlertOutPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($MetricsJsonPath)) {
  $MetricsJsonPath = Join-Path $WorkspaceRoot "docs\final\artifacts\one_plus_three_window_metrics_latest.json"
}
if ([string]::IsNullOrWhiteSpace($PolicyJsonPath)) {
  $PolicyJsonPath = Join-Path $WorkspaceRoot "docs\final\artifacts\one_plus_three_threshold_policy_v1.json"
}
if ([string]::IsNullOrWhiteSpace($OutputJsonPath)) {
  $OutputJsonPath = Join-Path $WorkspaceRoot "docs\final\artifacts\one_plus_three_gate_decision_latest.json"
}
if ([string]::IsNullOrWhiteSpace($SummaryOutPath)) {
  $SummaryOutPath = Join-Path $WorkspaceRoot "docs\final\artifacts\one_plus_three_daily_gate_summary_latest.json"
}
if ([string]::IsNullOrWhiteSpace($LogJsonlPath)) {
  $LogJsonlPath = Join-Path $WorkspaceRoot "reports\one_plus_three_daily_gate_log.jsonl"
}
if ([string]::IsNullOrWhiteSpace($AlertOutPath)) {
  $AlertOutPath = Join-Path $WorkspaceRoot "docs\final\artifacts\one_plus_three_daily_gate_alert_latest.json"
}

$runner = Join-Path $WorkspaceRoot "scripts\run_one_plus_three_warning_critical_gate_v1.py"

function New-Step([string]$step, [bool]$ok, [string]$detail) {
  [pscustomobject]@{
    step = $step
    ok = $ok
    detail = $detail
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  }
}

$steps = @()

try {
  if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
  }
  if (-not (Test-Path -LiteralPath $PolicyJsonPath)) {
    throw "Policy not found: $PolicyJsonPath"
  }
  if (-not (Test-Path -LiteralPath $MetricsJsonPath)) {
    throw "Metrics not found: $MetricsJsonPath"
  }

  Set-Location -LiteralPath $WorkspaceRoot

  py $runner --metrics-json $MetricsJsonPath --policy-json $PolicyJsonPath --output $OutputJsonPath
  if ($LASTEXITCODE -ne 0) { throw "run_one_plus_three_warning_critical_gate_v1.py exit=$LASTEXITCODE" }
  $steps += New-Step "run_one_plus_three_gate" $true "decision generated"

  $decision = Get-Content -Raw -LiteralPath $OutputJsonPath | ConvertFrom-Json
  $gateLevel = [string]$decision.gate_level
  $severity = switch ($gateLevel) {
    "critical" { "critical" }
    "warning" { "warning" }
    default { "ok" }
  }
  $status = if ($gateLevel -eq "ok") { "PASS" } else { "HOLD" }

  $summary = [pscustomobject]@{
    schema = "one_plus_three_daily_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = $status
    severity = $severity
    gate_level = $gateLevel
    reason_codes = @($decision.reason_codes)
    actions = @($decision.actions)
    decision_path = $OutputJsonPath
    metrics_path = $MetricsJsonPath
    policy_path = $PolicyJsonPath
    steps = $steps
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryOutPath -Encoding UTF8

  $line = [pscustomobject]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    schema = "one_plus_three_daily_gate_log_v1"
    status = $status
    severity = $severity
    gate_level = $gateLevel
    reason_codes = @($decision.reason_codes)
    summary_path = $SummaryOutPath
  } | ConvertTo-Json -Depth 6 -Compress
  Add-Content -LiteralPath $LogJsonlPath -Value $line -Encoding UTF8

  if ($status -ne "PASS") {
    $alert = [pscustomobject]@{
      schema = "one_plus_three_daily_gate_alert_v1"
      generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
      severity = $severity
      title = "1+3 daily gate is HOLD"
      message = "gate_level=$gateLevel reasons=$($decision.reason_codes -join ',')"
      summary_path = $SummaryOutPath
      decision_path = $OutputJsonPath
      metrics_path = $MetricsJsonPath
    }
    $alert | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $AlertOutPath -Encoding UTF8

    $webhook = ""
    if ($severity -eq "critical") {
      $webhook = $env:ONE_PLUS_THREE_CRITICAL_WEBHOOK_URL
      if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:ONE_PLUS_THREE_GATE_WEBHOOK_URL
      }
    }
    else {
      $webhook = $env:ONE_PLUS_THREE_WARNING_WEBHOOK_URL
      if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:ONE_PLUS_THREE_GATE_WEBHOOK_URL
      }
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
      $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }

    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
      try {
        Invoke-RestMethod -Method Post -Uri $webhook -ContentType "application/json" -Body ($alert | ConvertTo-Json -Depth 6) | Out-Null
      }
      catch {
        $steps += New-Step "webhook_notify" $false $_.Exception.Message
      }
    }
  }
  elseif (Test-Path -LiteralPath $AlertOutPath) {
    Remove-Item -LiteralPath $AlertOutPath -Force -ErrorAction SilentlyContinue
    $steps += New-Step "clear_stale_alert" $true "removed previous HOLD alert artifact"
  }

  Write-Host "[ok] one_plus_three daily gate -> $SummaryOutPath"
  exit 0
}
catch {
  $steps += New-Step "pipeline_exception" $false $_.Exception.Message
  $summary = [pscustomobject]@{
    schema = "one_plus_three_daily_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    status = "FAIL"
    error = $_.Exception.Message
    decision_path = $OutputJsonPath
    metrics_path = $MetricsJsonPath
    policy_path = $PolicyJsonPath
    steps = $steps
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryOutPath -Encoding UTF8
  Write-Host "[err] one_plus_three daily gate failed -> $SummaryOutPath"
  exit 1
}
