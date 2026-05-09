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
$cooldownHours = 0.5
if (Test-Path -LiteralPath $policyPath) {
  try {
    $policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
    if ($policy -and $policy.guardian_bundle_alert -and $null -ne $policy.guardian_bundle_alert.cooldown_hours) {
      $cooldownHours = [double]$policy.guardian_bundle_alert.cooldown_hours
    }
  } catch {
    Write-Host "[warn] trading_guardian_policy parse failed, using drill default cooldown"
  }
}

$drill = Join-Path $WorkspaceRoot "scripts\run_trading_guardian_daily_drill_v1.py"
if (-not (Test-Path -LiteralPath $drill)) { throw "Missing script: $drill" }

py $drill --workspace-root $WorkspaceRoot --cooldown-hours $cooldownHours
if ($LASTEXITCODE -ne 0) {
  throw "run_trading_guardian_daily_drill_v1.py exit $LASTEXITCODE"
}

Write-Host "[ok] trading guardian daily drill complete"
exit 0
