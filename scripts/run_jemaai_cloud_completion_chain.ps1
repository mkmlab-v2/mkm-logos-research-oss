# Fused "completion" run toward jemaai.cloud: Fact-Lock + P1 A/B + Thin/BTC anchor + Sasang + jemaai MVP file checks.
# Does NOT deploy nginx or start VPS services — local/ops validation only.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_jemaai_cloud_completion_chain.ps1
#
# Faster (skip P1 A/B bundle — long):
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_jemaai_cloud_completion_chain.ps1 -SkipP1AB

param(
    [switch]$SkipP1AB
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

$autoArgs = @("-File", (Join-Path $workspaceRoot "scripts\run_workspace_autopilot_chain.ps1"), "-IncludeJemaaiCloudChecks")
if (-not $SkipP1AB) {
    $autoArgs += "-IncludeP1AB"
}

Write-Host "=== jemaai.cloud completion chain (autopilot + jemaai checks$(if (-not $SkipP1AB) { ' + P1 A/B' })) ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass @autoArgs
exit $LASTEXITCODE
