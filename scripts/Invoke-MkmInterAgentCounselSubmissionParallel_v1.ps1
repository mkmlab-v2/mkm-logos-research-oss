#Requires -Version 5.1
<#
.SYNOPSIS
  Commander-authorized legal submission: manifest + capture + readiness + smoke.

.EXAMPLE
  powershell -File scripts\Invoke-MkmInterAgentCounselSubmissionParallel_v1.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== Commander legal submission (sync) ==" -ForegroundColor Cyan
py scripts/record_mkm_inter_agent_commander_legal_submission_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$jobs = @()
$jobs += Start-Job -ScriptBlock {
    Set-Location $using:root
    py scripts/build_mkm_inter_agent_counsel_export_manifest_v1.py
}
$jobs += Start-Job -ScriptBlock {
    Set-Location $using:root
    py scripts/capture_mkm_inter_agent_first_message_live_http_v1.py
}
$jobs += Start-Job -ScriptBlock {
    Set-Location $using:root
    py scripts/build_mkm_inter_agent_post_commander_approval_bundle_v1.py --refresh-status
}

Write-Host "== Parallel ($($jobs.Count) jobs) ==" -ForegroundColor Cyan
$jobs | Wait-Job | Out-Null
foreach ($j in $jobs) {
    Receive-Job -Job $j | ForEach-Object { Write-Host $_ }
    if ($j.State -ne "Completed") { Remove-Job $j -Force; exit 1 }
    Write-Host "[OK] Job $($j.Id)" -ForegroundColor Green
    Remove-Job -Job $j -Force
}

Write-Host "== Encoding smoke ==" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmInterAgentEncodingSmoke_v1.ps1 -SkipDialogueMock
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Handoff + closure readiness (after status) ==" -ForegroundColor Cyan
py scripts/build_mkm_inter_agent_legal_handoff_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py scripts/build_mkm_inter_agent_rq019_closure_readiness_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] Counsel submission parallel OK" -ForegroundColor Green
