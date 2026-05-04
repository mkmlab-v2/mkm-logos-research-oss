param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$LoopMatrixPath = "docs/final/artifacts/btc_loop_interval_matrix_latest.json",
  [string]$TaskName = "Bitcoin-V2-Execute-Guarded-Adaptive",
  [string]$ProjectRoot = "C:\workspace\projects\bitcoin-trading",
  [string]$StatePath = "projects/bitcoin-trading/memory/v2/ops/best_loop_task_state_latest.json",
  [string]$AuditLogPath = "projects/bitcoin-trading/memory/v2/ops/best_loop_task_state_log.jsonl",
  [int]$SkipNoChangeAlertThreshold = 3,
  [double]$MinBestTestScore = 0.0,
  [double]$MinBestStability = 0.9,
  [switch]$ApplyOnChangeOnly,
  [switch]$Apply
)

$ErrorActionPreference = "Stop"
Set-Location $WorkspaceRoot

if (-not [System.IO.Path]::IsPathRooted($LoopMatrixPath)) {
  $LoopMatrixPath = Join-Path $WorkspaceRoot $LoopMatrixPath
}
if (-not [System.IO.Path]::IsPathRooted($StatePath)) {
  $StatePath = Join-Path $WorkspaceRoot $StatePath
}
if (-not [System.IO.Path]::IsPathRooted($AuditLogPath)) {
  $AuditLogPath = Join-Path $WorkspaceRoot $AuditLogPath
}
if (-not (Test-Path -LiteralPath $LoopMatrixPath)) {
  throw "Loop matrix artifact not found: $LoopMatrixPath"
}

$doc = Get-Content -Raw -LiteralPath $LoopMatrixPath | ConvertFrom-Json
$bestHours = [int]$doc.recommended.best_loop_hours
if ($bestHours -le 0) {
  throw "Invalid best_loop_hours in artifact: $bestHours"
}
$minutes = $bestHours * 60

$bestRow = $null
if ($null -ne $doc.results) {
  foreach ($r in $doc.results) {
    if ([int]$r.loop_hours -eq $bestHours) {
      $bestRow = $r
      break
    }
  }
}
$bestTestScore = $null
$bestStability = $null
if ($null -ne $bestRow) {
  if ($null -ne $bestRow.test_score) { $bestTestScore = [double]$bestRow.test_score }
  if ($null -ne $bestRow.stability) { $bestStability = [double]$bestRow.stability }
}
$qualityReasons = @()
if ($null -eq $bestTestScore) {
  $qualityReasons += "missing_test_score"
} elseif ($bestTestScore -lt $MinBestTestScore) {
  $qualityReasons += "test_score_below_threshold($bestTestScore < $MinBestTestScore)"
}
if ($null -eq $bestStability) {
  $qualityReasons += "missing_stability"
} elseif ($bestStability -lt $MinBestStability) {
  $qualityReasons += "stability_below_threshold($bestStability < $MinBestStability)"
}
$qualityGatePassed = ($qualityReasons.Count -eq 0)

$runner = Join-Path $ProjectRoot "ops\v2\tasks\run_execute_cycle_guarded.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Guarded execute runner not found: $runner"
}
$tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

$preview = [ordered]@{
  schema = "best_loop_execute_task_preview_v1"
  loop_matrix_path = $LoopMatrixPath
  best_loop_hours = $bestHours
  schedule_minutes = $minutes
  task_name = $TaskName
  command = $tr
  apply = [bool]$Apply
  apply_on_change_only = [bool]$ApplyOnChangeOnly
  skip_no_change_alert_threshold = $SkipNoChangeAlertThreshold
  min_best_test_score = $MinBestTestScore
  min_best_stability = $MinBestStability
  best_test_score = $bestTestScore
  best_stability = $bestStability
  quality_gate_passed = $qualityGatePassed
  quality_gate_reasons = @($qualityReasons)
  state_path = $StatePath
  audit_log_path = $AuditLogPath
}
$previewJson = $preview | ConvertTo-Json -Depth 4
Write-Host $previewJson

if (-not $Apply) {
  Write-Host "Preview only. Pass -Apply to register/update scheduled task."
  exit 0
}

if (-not $qualityGatePassed) {
  Write-Host "Quality gate blocked task apply: $($qualityReasons -join ', ')" -ForegroundColor Yellow
  $fallbackAction = "keep_current_schedule"
  $blockEvent = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    task_name = $TaskName
    action = "block_quality_gate"
    fallback_action = $fallbackAction
    best_loop_hours = $bestHours
    best_test_score = $bestTestScore
    best_stability = $bestStability
    min_best_test_score = $MinBestTestScore
    min_best_stability = $MinBestStability
    reasons = @($qualityReasons)
    loop_matrix_path = $LoopMatrixPath
  } | ConvertTo-Json -Compress
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $AuditLogPath) | Out-Null
  Add-Content -LiteralPath $AuditLogPath -Value $blockEvent

  $stateDoc = [ordered]@{
    schema = "best_loop_task_state_v1"
    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    task_name = $TaskName
    best_loop_hours = $bestHours
    schedule_minutes = $minutes
    loop_matrix_path = $LoopMatrixPath
    last_action = "block_quality_gate"
    fallback_action = $fallbackAction
    quality_gate_passed = $false
    quality_gate_reasons = @($qualityReasons)
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StatePath) | Out-Null
  $stateDoc | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatePath -Encoding UTF8

  $webhook = $env:BEST_LOOP_TASK_ALARM_WEBHOOK_URL
  if ([string]::IsNullOrWhiteSpace($webhook)) {
    $webhook = $env:OPS_ALARM_WEBHOOK_URL
  }
  if (-not [string]::IsNullOrWhiteSpace($webhook)) {
    $payload = [ordered]@{
      event = "best_loop_task_quality_gate_block"
      ts_utc = (Get-Date).ToUniversalTime().ToString("o")
      task_name = $TaskName
      fallback_action = $fallbackAction
      best_loop_hours = $bestHours
      best_test_score = $bestTestScore
      best_stability = $bestStability
      min_best_test_score = $MinBestTestScore
      min_best_stability = $MinBestStability
      quality_gate_reasons = @($qualityReasons)
      loop_matrix_path = $LoopMatrixPath
    } | ConvertTo-Json -Depth 6 -Compress
    try {
      $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $payload -ContentType "application/json; charset=utf-8" -TimeoutSec 20
      Write-Host "Quality-gate block alert sent." -ForegroundColor Yellow
    } catch {
      Write-Host "Quality-gate block alert failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }
  exit 0
}

$prevHours = $null
$prevState = $null
if (Test-Path -LiteralPath $StatePath) {
  try {
    $prevState = Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
    if ($null -ne $prevState.best_loop_hours) { $prevHours = [int]$prevState.best_loop_hours }
  } catch {
    $prevHours = $null
    $prevState = $null
  }
}

$changed = ($prevHours -ne $bestHours)
if ($ApplyOnChangeOnly -and (-not $changed)) {
  Write-Host "No loop-hour change detected ($bestHours h). Skip task update."
  $skipEvent = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    task_name = $TaskName
    action = "skip_no_change"
    best_loop_hours = $bestHours
    previous_loop_hours = $prevHours
    schedule_minutes = $minutes
    loop_matrix_path = $LoopMatrixPath
  } | ConvertTo-Json -Compress
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $AuditLogPath) | Out-Null
  Add-Content -LiteralPath $AuditLogPath -Value $skipEvent

  # Update state even when skipped (for drift visibility + alert dedupe)
  $lastAlertedSkip = 0
  if ($null -ne $prevState -and $null -ne $prevState.last_alerted_skip_streak) {
    $lastAlertedSkip = [int]$prevState.last_alerted_skip_streak
  }

  $skipStreak = 0
  if (Test-Path -LiteralPath $AuditLogPath) {
    $lines = Get-Content -LiteralPath $AuditLogPath
    for ($idx = $lines.Count - 1; $idx -ge 0; $idx--) {
      $line = $lines[$idx]
      if ([string]::IsNullOrWhiteSpace($line)) { continue }
      try { $evt = $line | ConvertFrom-Json } catch { break }
      if ($evt.task_name -ne $TaskName) { break }
      if ($evt.action -eq "skip_no_change") {
        $skipStreak += 1
        continue
      }
      break
    }
  }

  $stateDoc = [ordered]@{
    schema = "best_loop_task_state_v1"
    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    task_name = $TaskName
    best_loop_hours = $bestHours
    schedule_minutes = $minutes
    loop_matrix_path = $LoopMatrixPath
    last_action = "skip_no_change"
    skip_no_change_streak = $skipStreak
    last_alerted_skip_streak = $lastAlertedSkip
  }

  $webhook = $env:BEST_LOOP_TASK_ALARM_WEBHOOK_URL
  if ([string]::IsNullOrWhiteSpace($webhook)) {
    $webhook = $env:OPS_ALARM_WEBHOOK_URL
  }
  if (
    $SkipNoChangeAlertThreshold -gt 0 -and
    $skipStreak -ge $SkipNoChangeAlertThreshold -and
    $skipStreak -gt $lastAlertedSkip -and
    (-not [string]::IsNullOrWhiteSpace($webhook))
  ) {
    $runbookUrl = $env:BEST_LOOP_TASK_EXPERIMENT_RUNBOOK_URL
    if ([string]::IsNullOrWhiteSpace($runbookUrl)) {
      $runbookUrl = $env:OPS_RUNBOOK_URL
    }
    if ([string]::IsNullOrWhiteSpace($runbookUrl)) {
      $runbookUrl = ""
    }
    $runbookMissing = [string]::IsNullOrWhiteSpace($runbookUrl)

    $matrixBestScore = $null
    $matrixTop3 = @()
    try {
      if ($null -ne $doc.recommended -and $null -ne $doc.recommended.best_score) {
        $matrixBestScore = [double]$doc.recommended.best_score
      }
      if ($null -ne $doc.results) {
        $top = @($doc.results | Select-Object -First 3)
        foreach ($r in $top) {
          $matrixTop3 += [ordered]@{
            loop_hours = $r.loop_hours
            score = $r.score
            total_return = $r.total_return
            max_drawdown = $r.max_drawdown
            trades = $r.trades
          }
        }
      }
    } catch {
      $matrixBestScore = $null
      $matrixTop3 = @()
    }

    $history = @()
    if (Test-Path -LiteralPath $AuditLogPath) {
      $lines = Get-Content -LiteralPath $AuditLogPath
      for ($idx = $lines.Count - 1; $idx -ge 0; $idx--) {
        $line = $lines[$idx]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $evt = $line | ConvertFrom-Json } catch { continue }
        if ($evt.task_name -ne $TaskName) { continue }
        $history += [ordered]@{
          ts_utc = $evt.ts_utc
          action = $evt.action
          best_loop_hours = $evt.best_loop_hours
          schedule_minutes = $evt.schedule_minutes
        }
        if ($history.Count -ge 5) { break }
      }
    }

    $payload = [ordered]@{
      event = "best_loop_task_skip_streak_alert"
      ts_utc = (Get-Date).ToUniversalTime().ToString("o")
      task_name = $TaskName
      skip_no_change_streak = $skipStreak
      threshold = $SkipNoChangeAlertThreshold
      best_loop_hours = $bestHours
      schedule_minutes = $minutes
      best_score = $matrixBestScore
      loop_matrix_path = $LoopMatrixPath
      runbook_url = $runbookUrl
      runbook_missing = $runbookMissing
      rank_top3 = @($matrixTop3)
      recent_history = @($history)
    }

    $decisionHint = "maintain"
    $decisionReason = "default_conservative"
    try {
      $top = @($matrixTop3)
      if ($top.Count -ge 2) {
        $bestScoreVal = [double]$top[0].score
        $secondScoreVal = [double]$top[1].score
        $scoreGap = $bestScoreVal - $secondScoreVal
        if ($bestScoreVal -lt 0.0) {
          $decisionHint = "consider_experiment"
          $decisionReason = "best_score_negative"
        } elseif ($scoreGap -lt 0.01 -and $skipStreak -ge ($SkipNoChangeAlertThreshold + 2)) {
          $decisionHint = "consider_experiment"
          $decisionReason = "narrow_score_gap_with_long_skip_streak"
        } else {
          $decisionHint = "maintain"
          $decisionReason = "best_score_and_gap_support_current_loop"
        }
        $payload.score_gap_best_vs_second = [Math]::Round($scoreGap, 6)
      } elseif ($null -ne $matrixBestScore -and [double]$matrixBestScore -lt 0.0) {
        $decisionHint = "consider_experiment"
        $decisionReason = "single_rank_negative_score"
      }
    } catch {
      $decisionHint = "maintain"
      $decisionReason = "decision_hint_fallback"
    }
    $payload.decision_hint = $decisionHint
    $payload.decision_reason = $decisionReason

    $payload = $payload | ConvertTo-Json -Depth 6 -Compress
    try {
      $null = Invoke-RestMethod -Uri $webhook -Method Post -Body $payload -ContentType "application/json; charset=utf-8" -TimeoutSec 20
      $stateDoc.last_alerted_skip_streak = $skipStreak
      Write-Host "Skip-streak alert sent (streak=$skipStreak)." -ForegroundColor Yellow

      # Optional secondary channel: experiment hint only
      $experimentWebhook = $env:BEST_LOOP_TASK_EXPERIMENT_WEBHOOK_URL
      if (
        $decisionHint -eq "consider_experiment" -and
        (-not [string]::IsNullOrWhiteSpace($experimentWebhook))
      ) {
        try {
          $null = Invoke-RestMethod -Uri $experimentWebhook -Method Post -Body $payload -ContentType "application/json; charset=utf-8" -TimeoutSec 20
          Write-Host "Experiment-channel alert sent." -ForegroundColor Yellow
        } catch {
          Write-Host "Experiment-channel alert failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
      }
    } catch {
      Write-Host "Skip-streak alert failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }

  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StatePath) | Out-Null
  $stateDoc | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $StatePath -Encoding UTF8
  exit 0
}

schtasks /Delete /TN $TaskName /F | Out-Null 2>&1
schtasks /Create /TN $TaskName /SC MINUTE /MO $minutes /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to create scheduled task. ExitCode=$LASTEXITCODE"
}
Write-Host "Created/updated scheduled task: $TaskName (every $minutes minutes)"

$stateDoc = [ordered]@{
  schema = "best_loop_task_state_v1"
  updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  task_name = $TaskName
  best_loop_hours = $bestHours
  schedule_minutes = $minutes
  loop_matrix_path = $LoopMatrixPath
  last_action = "apply"
  skip_no_change_streak = 0
  last_alerted_skip_streak = 0
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StatePath) | Out-Null
$stateDoc | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatePath -Encoding UTF8

$applyEvent = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  task_name = $TaskName
  action = "apply"
  best_loop_hours = $bestHours
  previous_loop_hours = $prevHours
  schedule_minutes = $minutes
  loop_matrix_path = $LoopMatrixPath
  apply_on_change_only = [bool]$ApplyOnChangeOnly
} | ConvertTo-Json -Compress
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $AuditLogPath) | Out-Null
Add-Content -LiteralPath $AuditLogPath -Value $applyEvent

