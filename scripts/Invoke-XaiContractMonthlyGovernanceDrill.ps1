param(
  [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\run_xai_contract_monthly_governance_drill_v1.ps1"

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $runner `
  -WorkspaceRoot $WorkspaceRoot `
  -NormalMinPassRate 0.95 `
  -NormalCriticalPassRate 0.85 `
  -DrillMinPassRate 1.1 `
  -DrillCriticalPassRate 1.05

exit $LASTEXITCODE
