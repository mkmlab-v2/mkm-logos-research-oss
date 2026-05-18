#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel B-track lanes: low-saving sweep refresh + A2A dialogue routing compare (health).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmInterAgentParallelLanes_v1.ps1
#>
param(
    [switch]$SkipSweep,
    [switch]$SkipDialogueCompare
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$jobs = @()
if (-not $SkipSweep) {
    $jobs += Start-Job -ScriptBlock {
        Set-Location $using:root
        py scripts/run_compression_low_saving_local_cap_sweep_v1.py
    }
}
if (-not $SkipDialogueCompare) {
    $jobs += Start-Job -ScriptBlock {
        Set-Location $using:root
        py scripts/run_mkm_inter_agent_dialogue_routing_compare_v1.py --scenario health --turns 4
    }
}

if ($jobs.Count -eq 0) {
    Write-Host "[SKIP] No lanes selected." -ForegroundColor Yellow
    exit 0
}

Write-Host "== Waiting for $($jobs.Count) parallel lane(s) ==" -ForegroundColor Cyan
$jobs | Wait-Job | Out-Null
$failed = 0
foreach ($j in $jobs) {
    $out = Receive-Job -Job $j -Wait -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($j.State -ne "Completed") {
        $failed++
        Write-Host "[FAIL] Job $($j.Id) state=$($j.State)" -ForegroundColor Red
    } else {
        Write-Host "[OK] Job $($j.Id)" -ForegroundColor Green
    }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}
if ($failed -gt 0) { exit 1 }
Write-Host "[DONE] Parallel lanes OK" -ForegroundColor Green
