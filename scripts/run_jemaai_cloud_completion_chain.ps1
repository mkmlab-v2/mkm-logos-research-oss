# Fused "completion" run toward jemaai.cloud: Fact-Lock + P1 A/B + Thin/BTC anchor + Sasang + jemaai MVP file checks
# (includes compression_v2_explorer.html + Serve/Start-CompressionV2Explorer scripts when -IncludeJemaaiCloudChecks).
# Does NOT deploy nginx or start VPS services — local/ops validation only.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_jemaai_cloud_completion_chain.ps1
#
# Faster (skip P1 A/B bundle — long):
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_jemaai_cloud_completion_chain.ps1 -SkipP1AB
#
# Optional showroom regeneration (local artifacts only):
#   powershell ... -IncludeShowroomTrackCChain
#
# Multitarget B_track pre-gate (Kaggle/bio) is optional for jemaai MVP file checks; default is -SkipMultitargetPreGate on the inner autopilot.
# To require it: -RequireMultitargetPreGate (needs scripts/build_multitarget_label_topology_report_v1.py and related artifacts).

param(
    [switch]$SkipP1AB,
    [switch]$IncludeE2ESmoke,
    [switch]$IncludeShowroomTrackCChain,
    [switch]$RequireMultitargetPreGate
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

$autoArgs = @("-File", (Join-Path $workspaceRoot "scripts\run_workspace_autopilot_chain.ps1"), "-IncludeJemaaiCloudChecks")
if (-not $RequireMultitargetPreGate) {
    $autoArgs += "-SkipMultitargetPreGate"
}
if (-not $SkipP1AB) {
    $autoArgs += "-IncludeP1AB"
}
if ($IncludeE2ESmoke) {
    $autoArgs += "-IncludeJemaaiE2ESmoke"
}
if ($IncludeShowroomTrackCChain) {
    $autoArgs += "-IncludeShowroomTrackCChain"
}

Write-Host "=== jemaai.cloud completion chain (autopilot + jemaai checks$(if (-not $SkipP1AB) { ' + P1 A/B' })$(if ($IncludeE2ESmoke) { ' + E2E smoke' })$(if ($IncludeShowroomTrackCChain) { ' + Track C showroom' })) ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass @autoArgs
exit $LASTEXITCODE
