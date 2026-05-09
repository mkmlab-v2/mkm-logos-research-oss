[CmdletBinding()]
param(
  [string]$WorkspaceRoot = ""
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

$policyPath = Join-Path $WorkspaceRoot "reports\trading_guardian_policy_latest.json"
$bundleAlertCooldownHours = 0.5
if (Test-Path -LiteralPath $policyPath) {
  try {
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    if ($policy -and $policy.guardian_bundle_alert -and $null -ne $policy.guardian_bundle_alert.cooldown_hours) {
      $bundleAlertCooldownHours = [double]$policy.guardian_bundle_alert.cooldown_hours
    }
  } catch {
    Write-Host "[warn] trading_guardian_policy parse failed, using bundle alert default cooldown"
  }
}

$healthTask = Join-Path $WorkspaceRoot "scripts\Run-TradingAutomationHealthTask.ps1"
$coverageTask = Join-Path $WorkspaceRoot "scripts\Run-ProtectiveCoverageGuardTask.ps1"
$buildBundle = Join-Path $WorkspaceRoot "scripts\build_trading_guardian_bundle_status_v1.py"
$buildOps = Join-Path $WorkspaceRoot "scripts\build_trading_guardian_ops_snapshot_v1.py"
$bundleAlert = Join-Path $WorkspaceRoot "scripts\send_trading_guardian_bundle_alert_v1.py"
if (-not (Test-Path -LiteralPath $healthTask)) { throw "Missing script: $healthTask" }
if (-not (Test-Path -LiteralPath $coverageTask)) { throw "Missing script: $coverageTask" }
if (-not (Test-Path -LiteralPath $buildBundle)) { throw "Missing script: $buildBundle" }
if (-not (Test-Path -LiteralPath $buildOps)) { throw "Missing script: $buildOps" }
if (-not (Test-Path -LiteralPath $bundleAlert)) { throw "Missing script: $bundleAlert" }

pwsh -NoProfile -ExecutionPolicy Bypass -File $healthTask -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
  throw "Run-TradingAutomationHealthTask.ps1 exit $LASTEXITCODE"
}

pwsh -NoProfile -ExecutionPolicy Bypass -File $coverageTask -WorkspaceRoot $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
  throw "Run-ProtectiveCoverageGuardTask.ps1 exit $LASTEXITCODE"
}

py $buildBundle --workspace-root $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
  throw "build_trading_guardian_bundle_status_v1.py exit $LASTEXITCODE"
}

py $bundleAlert --workspace-root $WorkspaceRoot --cooldown-hours $bundleAlertCooldownHours
if ($LASTEXITCODE -ne 0) {
  throw "send_trading_guardian_bundle_alert_v1.py exit $LASTEXITCODE"
}

py $buildOps --workspace-root $WorkspaceRoot
if ($LASTEXITCODE -ne 0) {
  throw "build_trading_guardian_ops_snapshot_v1.py exit $LASTEXITCODE"
}

Write-Host "[ok] trading guardian bundle: health+coverage complete"
exit 0
