# B-track codebook/codepack promotion chain (no sidecar dependency):
#   drift (--strict) -> insight bridge inventory -> promotion bridge index -> signoff packet.
# Run from repo root. Use after codepack/LG integrity report changes; updates docs/final/artifacts/*_latest.json.
# Scheduled task helper: scripts/register_btrack_codebook_codepack_chain_task.ps1

param(
    [switch]$SkipSignoff
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location -LiteralPath $root

Write-Host "check_codebook_codepack_drift_v1.py --strict" -ForegroundColor DarkGray
& py "scripts/check_codebook_codepack_drift_v1.py" --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "build_btrack_insight_bridge_inventory_v1.py" -ForegroundColor DarkGray
& py "scripts/build_btrack_insight_bridge_inventory_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "build_btrack_insight_promotion_bridge_index_v1.py" -ForegroundColor DarkGray
& py "scripts/build_btrack_insight_promotion_bridge_index_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipSignoff) {
    Write-Host "build_btrack_promotion_signoff_packet_v1.py --separate-track-gates" -ForegroundColor DarkGray
    & py "scripts/build_btrack_promotion_signoff_packet_v1.py" --separate-track-gates
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK B-track codebook/codepack promotion chain." -ForegroundColor Green
exit 0
