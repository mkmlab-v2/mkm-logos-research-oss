#Requires -Version 5.1
<#
.SYNOPSIS
  Post-commander-approval parallel bundle: smoke + post-approval evidence + status.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmInterAgentPostApprovalBundle_v1.ps1
#>
param(
    [switch]$SkipSmoke,
    [switch]$SkipParallelLanes
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json")) {
    Write-Host "[FAIL] Missing commander approval JSON. Run record_mkm_inter_agent_health_commander_approval_v1.py first." -ForegroundColor Red
    exit 1
}

$jobs = @(
    Start-Job -ScriptBlock {
        Set-Location $using:root
        py scripts/build_mkm_inter_agent_post_commander_approval_bundle_v1.py --refresh-status
    }
)
if (-not $SkipParallelLanes) {
    $jobs += Start-Job -ScriptBlock {
        Set-Location $using:root
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmInterAgentParallelLanes_v1.ps1 -SkipCommanderApproval
    }
}

Write-Host "== Waiting for $($jobs.Count) parallel job(s) ==" -ForegroundColor Cyan
$jobs | Wait-Job | Out-Null
$failed = 0
foreach ($j in $jobs) {
    $out = Receive-Job -Job $j -Wait -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($j.State -ne "Completed") { $failed++; Write-Host "[FAIL] Job $($j.Id)" -ForegroundColor Red }
    else { Write-Host "[OK] Job $($j.Id)" -ForegroundColor Green }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}
if ($failed -gt 0) { exit 1 }

if (-not $SkipSmoke) {
    Write-Host "== Encoding smoke ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmInterAgentEncodingSmoke_v1.ps1 -SkipDialogueMock
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[DONE] Post-approval bundle OK" -ForegroundColor Green
