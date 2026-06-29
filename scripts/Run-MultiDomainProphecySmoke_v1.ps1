# Multi-domain prophecy smoke — registry + router map + dry-run loop [B-track].
# Usage: pwsh -NoProfile -File scripts\Run-MultiDomainProphecySmoke_v1.ps1 [-SkipDailyLoopDryRun]

param(
    [switch]$SkipDailyLoopDryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Write-Host "`n=== [1/5] domain_prophecy registry gate ===" -ForegroundColor Cyan
& py scripts/check_domain_prophecy_registry_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== [2/5] smoke coverage gate (all domain_ids mapped) ===" -ForegroundColor Cyan
& py scripts/check_domain_prophecy_smoke_coverage_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== [3/5] shallow router map self-test ===" -ForegroundColor Cyan
& py scripts/route_domain_prophecy_from_shallow_v1.py --self-test
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipDailyLoopDryRun) {
    Write-Host "`n=== [4/5] domain daily loop dry-run (all active) ===" -ForegroundColor Cyan
    & py scripts/run_domain_prophecy_daily_loop_v1.py --phase evening --dry-run
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "`n=== [5/5] domain prophecy P4 pytest ===" -ForegroundColor Cyan
& py -m pytest tests/test_domain_prophecy_p4_v1.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nOK: multi-domain prophecy smoke completed." -ForegroundColor Green
exit 0
