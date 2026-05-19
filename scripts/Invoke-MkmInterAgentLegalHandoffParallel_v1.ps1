#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel: legal handoff pack + post-approval bundle + encoding smoke (RQ-019 pre-legal).

.EXAMPLE
  powershell -File scripts\Invoke-MkmInterAgentLegalHandoffParallel_v1.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$jobs = @()
$jobs += Start-Job -ScriptBlock {
    Set-Location $using:root
    py scripts/build_mkm_inter_agent_post_commander_approval_bundle_v1.py --refresh-status
}
$jobs += Start-Job -ScriptBlock {
    Set-Location $using:root
    py scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py
}

Write-Host "== Legal handoff parallel ($($jobs.Count) jobs) ==" -ForegroundColor Cyan
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

Write-Host "== Legal handoff pack (after status refresh) ==" -ForegroundColor Cyan
py scripts/build_mkm_inter_agent_legal_handoff_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] Legal handoff parallel OK" -ForegroundColor Green
