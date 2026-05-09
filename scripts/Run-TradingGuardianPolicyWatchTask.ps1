[CmdletBinding()]
param(
  [string]$WorkspaceRoot = "",
  [switch]$SnapshotBaseline,
  [switch]$AcknowledgePolicyBaselineUpdate,
  [string]$Reason = ""
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

$ensurePolicy = Join-Path $WorkspaceRoot "scripts\Ensure-TradingGuardianPolicyFromTemplate.ps1"
if (Test-Path -LiteralPath $ensurePolicy) {
  & $ensurePolicy -WorkspaceRoot $WorkspaceRoot
}

$check = Join-Path $WorkspaceRoot "scripts\check_trading_guardian_policy_drift_v1.py"
$alert = Join-Path $WorkspaceRoot "scripts\send_trading_guardian_policy_drift_alert_v1.py"
$policyPath = Join-Path $WorkspaceRoot "reports\trading_guardian_policy_latest.json"
$statePath = Join-Path $WorkspaceRoot "reports\trading_guardian_policy_hash_state_latest.json"
$approvalLogPath = Join-Path $WorkspaceRoot "reports\trading_guardian_policy_baseline_approvals.jsonl"
if (-not (Test-Path -LiteralPath $check)) { throw "Missing script: $check" }
if (-not (Test-Path -LiteralPath $alert)) { throw "Missing script: $alert" }

$policyWatchMode = "strict_drift_alert"
if (Test-Path -LiteralPath $policyPath) {
  try {
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    if ($policy -and $policy.policy_watch -and $policy.policy_watch.mode) {
      $policyWatchMode = "$($policy.policy_watch.mode)"
    }
  } catch {
    Write-Host "[warn] trading_guardian_policy parse failed, using strict_drift_alert mode"
  }
}

if ($SnapshotBaseline) {
  if (-not $AcknowledgePolicyBaselineUpdate) {
    throw "SnapshotBaseline requires -AcknowledgePolicyBaselineUpdate"
  }
  if ([string]::IsNullOrWhiteSpace($Reason)) {
    throw "SnapshotBaseline requires -Reason (change justification)"
  }

  $policyHashBefore = ""
  $baselineHashBefore = ""
  if (Test-Path -LiteralPath $policyPath) {
    try {
      $policyHashBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $policyPath).Hash.ToLowerInvariant()
    } catch {}
  }
  if (Test-Path -LiteralPath $statePath) {
    try {
      $prevState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
      if ($prevState -and $prevState.baseline_sha256) {
        $baselineHashBefore = "$($prevState.baseline_sha256)".ToLowerInvariant()
      }
    } catch {}
  }

  $approval = [ordered]@{
    schema = "trading_guardian_policy_baseline_approval_v1"
    approved_at_utc = [DateTime]::UtcNow.ToString("o")
    actor = "$env:USERNAME"
    mode = $policyWatchMode
    reason = $Reason.Trim()
    policy_hash_before = $policyHashBefore
    baseline_hash_before = $baselineHashBefore
  }
  $script:approvalRecord = $approval
}

$mode = if ($SnapshotBaseline) { "snapshot" } else { "check" }
py $check --workspace-root $WorkspaceRoot --mode $mode
$checkExit = $LASTEXITCODE

if ($SnapshotBaseline -and $script:approvalRecord) {
  $policyHashAfter = ""
  $baselineHashAfter = ""
  if (Test-Path -LiteralPath $policyPath) {
    try {
      $policyHashAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $policyPath).Hash.ToLowerInvariant()
    } catch {}
  }
  if (Test-Path -LiteralPath $statePath) {
    try {
      $nextState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
      if ($nextState -and $nextState.baseline_sha256) {
        $baselineHashAfter = "$($nextState.baseline_sha256)".ToLowerInvariant()
      }
    } catch {}
  }
  $script:approvalRecord.policy_hash_after = $policyHashAfter
  $script:approvalRecord.baseline_hash_after = $baselineHashAfter
  $approvalLine = $script:approvalRecord | ConvertTo-Json -Depth 8 -Compress
  Add-Content -LiteralPath $approvalLogPath -Value $approvalLine -Encoding UTF8
}

if (-not $SnapshotBaseline -and $checkExit -eq 1 -and $policyWatchMode -eq "auto_snapshot_on_drift") {
  Write-Host "[warn] policy drift detected - auto snapshot mode active, updating baseline"
  py $check --workspace-root $WorkspaceRoot --mode snapshot
  $checkExit = $LASTEXITCODE
}

py $alert --workspace-root $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
  throw "send_trading_guardian_policy_drift_alert_v1.py exit $LASTEXITCODE"
}

if ($checkExit -eq 0) {
  Write-Host "[ok] trading guardian policy watch: in sync / baseline updated (mode=$policyWatchMode)"
} elseif ($checkExit -eq 1) {
  Write-Host "[warn] trading guardian policy watch: drift detected (mode=$policyWatchMode, alert handled)"
} else {
  Write-Host "[warn] trading guardian policy watch: check runtime issue (exit=$checkExit)"
}
exit 0
