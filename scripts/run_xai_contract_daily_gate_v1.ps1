param(
  [string]$WorkspaceRoot = "C:\workspace",
  [double]$MinPassRate = 0.95,
  [double]$CriticalPassRate = 0.85,
  [switch]$BootstrapIfMissing,
  [switch]$AutoBuildRuntimeFromArtifacts = $true,
  [string]$EvalOutPath = "",
  [string]$FailuresOutPath = "",
  [string]$SummaryOutPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($EvalOutPath)) {
  $EvalOutPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_eval_latest.json"
}
if ([string]::IsNullOrWhiteSpace($FailuresOutPath)) {
  $FailuresOutPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_failures_latest.json"
}
if ([string]::IsNullOrWhiteSpace($SummaryOutPath)) {
  $SummaryOutPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_daily_gate_summary_latest.json"
}

$responsesPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_sample_20_eval_responses_latest.json"
$runtimeAnswersPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_runtime_answers_latest.json"
$runtimeArtifactBuilder = Join-Path $WorkspaceRoot "scripts\build_xai_runtime_answers_from_artifacts_v1.py"
$runtimeMapper = Join-Path $WorkspaceRoot "scripts\build_xai_responses_from_runtime_v1.py"
$runner = Join-Path $WorkspaceRoot "scripts\run_xai_contract_eval_v1.py"
$failTop5Builder = Join-Path $WorkspaceRoot "scripts\build_xai_contract_failures_top5_report_v1.py"
$alertPath = Join-Path $WorkspaceRoot "docs\final\artifacts\xai_contract_daily_gate_alert_latest.json"
$logPath = Join-Path $WorkspaceRoot "reports\xai_contract_daily_gate_log.jsonl"

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
  Set-Location -LiteralPath $WorkspaceRoot

  if ($BootstrapIfMissing -and -not (Test-Path -LiteralPath $responsesPath)) {
    py $runner --bootstrap-empty-responses
    if ($LASTEXITCODE -ne 0) { throw "bootstrap-empty-responses exit=$LASTEXITCODE" }
    $steps += New-Step "bootstrap_empty_responses" $true "responses created"
  }

  if ($AutoBuildRuntimeFromArtifacts -and -not (Test-Path -LiteralPath $runtimeAnswersPath) -and (Test-Path -LiteralPath $runtimeArtifactBuilder)) {
    py $runtimeArtifactBuilder --output $runtimeAnswersPath
    if ($LASTEXITCODE -ne 0) { throw "build_xai_runtime_answers_from_artifacts_v1.py exit=$LASTEXITCODE" }
    $steps += New-Step "build_runtime_from_artifacts" $true "runtime answers created from artifacts"
  }

  if ((Test-Path -LiteralPath $runtimeAnswersPath) -and (Test-Path -LiteralPath $runtimeMapper)) {
    py $runtimeMapper --input $runtimeAnswersPath --output $responsesPath
    if ($LASTEXITCODE -ne 0) { throw "build_xai_responses_from_runtime_v1.py exit=$LASTEXITCODE" }
    $steps += New-Step "map_runtime_answers" $true "runtime -> contract responses"
  }
  elseif (Test-Path -LiteralPath $runtimeAnswersPath) {
    $steps += New-Step "map_runtime_answers" $false "mapper_missing: $runtimeMapper"
  }

  py $runner --min-pass-rate $MinPassRate --output $EvalOutPath --failures-output $FailuresOutPath
  if ($LASTEXITCODE -ne 0) { throw "run_xai_contract_eval_v1.py exit=$LASTEXITCODE" }
  $steps += New-Step "run_eval" $true "min_pass_rate=$MinPassRate"

  $eval = Get-Content -Raw -LiteralPath $EvalOutPath | ConvertFrom-Json
  $decision = [string]$eval.decision
  $passRate = [double]$eval.metrics.pass_rate
  $status = if ($decision -eq "GO_CONTRACT_READY") { "PASS" } else { "HOLD" }
  $severity = if ($status -eq "PASS") { "ok" } elseif ($passRate -lt $CriticalPassRate) { "critical" } else { "warning" }

  $summary = [pscustomobject]@{
    schema = "xai_contract_daily_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    min_pass_rate = $MinPassRate
    decision = $decision
    status = $status
    severity = $severity
    pass_rate = $passRate
    critical_pass_rate = $CriticalPassRate
    eval_path = $EvalOutPath
    failures_path = $FailuresOutPath
    steps = $steps
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryOutPath -Encoding UTF8

  if ((Test-Path -LiteralPath $FailuresOutPath) -and (Test-Path -LiteralPath $failTop5Builder)) {
    py $failTop5Builder --input $FailuresOutPath
    if ($LASTEXITCODE -eq 0) {
      $steps += New-Step "build_failures_top5_report" $true "top5 report generated"
    } else {
      $steps += New-Step "build_failures_top5_report" $false "builder exit=$LASTEXITCODE"
    }
  }

  $line = [pscustomobject]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    schema = "xai_contract_daily_gate_log_v1"
    status = $status
    severity = $severity
    decision = $decision
    pass_rate = $passRate
    min_pass_rate = $MinPassRate
    critical_pass_rate = $CriticalPassRate
    summary_path = $SummaryOutPath
  } | ConvertTo-Json -Depth 4 -Compress
  Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8

  if ($status -ne "PASS") {
    $alert = [pscustomobject]@{
      schema = "xai_contract_daily_gate_alert_v1"
      generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
      severity = $severity
      title = "XAI contract daily gate is HOLD"
      message = "decision=$decision pass_rate=$passRate min_pass_rate=$MinPassRate critical_pass_rate=$CriticalPassRate"
      summary_path = $SummaryOutPath
      failures_path = $FailuresOutPath
    }
    $alert | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $alertPath -Encoding UTF8

    # Severity-aware webhook routing:
    # - critical: XAI_CONTRACT_GATE_CRITICAL_WEBHOOK_URL (fallback to generic)
    # - warning : XAI_CONTRACT_GATE_WARNING_WEBHOOK_URL (fallback to generic)
    $webhook = ""
    if ($severity -eq "critical") {
      $webhook = $env:XAI_CONTRACT_GATE_CRITICAL_WEBHOOK_URL
      if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:XAI_CONTRACT_GATE_WEBHOOK_URL
      }
    } else {
      $webhook = $env:XAI_CONTRACT_GATE_WARNING_WEBHOOK_URL
      if ([string]::IsNullOrWhiteSpace($webhook)) {
        $webhook = $env:XAI_CONTRACT_GATE_WEBHOOK_URL
      }
    }
    if ([string]::IsNullOrWhiteSpace($webhook)) {
      $webhook = $env:OPS_ALARM_WEBHOOK_URL
    }
    if (-not [string]::IsNullOrWhiteSpace($webhook)) {
      try {
        Invoke-RestMethod -Method Post -Uri $webhook -ContentType "application/json" -Body ($alert | ConvertTo-Json -Depth 6) | Out-Null
      } catch {
        $steps += New-Step "webhook_notify" $false $_.Exception.Message
      }
    }
  } elseif (Test-Path -LiteralPath $alertPath) {
    Remove-Item -LiteralPath $alertPath -Force -ErrorAction SilentlyContinue
    $steps += New-Step "clear_stale_alert" $true "removed previous HOLD alert artifact"
  }

  Write-Host "[ok] xai contract daily gate -> $SummaryOutPath"
  exit 0
}
catch {
  $steps += New-Step "pipeline_exception" $false $_.Exception.Message
  $summary = [pscustomobject]@{
    schema = "xai_contract_daily_gate_summary_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    min_pass_rate = $MinPassRate
    status = "FAIL"
    error = $_.Exception.Message
    eval_path = $EvalOutPath
    failures_path = $FailuresOutPath
    steps = $steps
  }
  $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryOutPath -Encoding UTF8
  Write-Host "[err] xai contract daily gate failed -> $SummaryOutPath"
  exit 1
}
