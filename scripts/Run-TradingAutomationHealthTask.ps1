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

$verify = Join-Path $WorkspaceRoot "scripts\Verify-TradingAutomationHealth.ps1"
$alert = Join-Path $WorkspaceRoot "scripts\send_trading_automation_health_alert_v1.py"
if (-not (Test-Path -LiteralPath $verify)) { throw "Missing script: $verify" }
if (-not (Test-Path -LiteralPath $alert)) { throw "Missing script: $alert" }

# Health check exit code reflects service health and is expected to be non-zero during incidents.
pwsh -NoProfile -ExecutionPolicy Bypass -File $verify -AllowExpectedSecurityDrift -AllowPolicyLockedGoNoGo
$verifyExit = $LASTEXITCODE

py $alert
if ($LASTEXITCODE -ne 0) {
  throw "send_trading_automation_health_alert_v1.py exit $LASTEXITCODE"
}

if ($verifyExit -eq 0) {
  Write-Host "[ok] trading automation health: GREEN"
} else {
  Write-Host "[warn] trading automation health: DEGRADED (alert handled)"
}
exit 0
