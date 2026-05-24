#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel lanes: Op30 FullParallel (skip LivePatrol) + Oracle/MS gate + B-track prereqs.
#>
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$reportPath = Join-Path $root "reports\next_parallel_lanes_v1_latest.json"
$lanes = @{}

Write-Host "== Parallel: Op30 FullParallel | Oracle+MS gate | B-track prereqs ==" -ForegroundColor Cyan

$j1 = Start-Job -Name "op30_full_parallel" -ScriptBlock {
    Set-Location $using:root
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $using:root "scripts\Invoke-Op30AutoRun_v1.ps1") -FullParallel -SkipLivePatrol
    exit $LASTEXITCODE
}
$j2 = Start-Job -Name "oracle_ms_gate" -ScriptBlock {
    Set-Location $using:root
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $using:root "scripts\Invoke-OracleMsParallelGate_v1.ps1")
    exit $LASTEXITCODE
}
$j3 = Start-Job -Name "btrack_prereqs" -ScriptBlock {
    Set-Location $using:root
    & py (Join-Path $using:root "scripts\check_btrack_prophecy_chain_prereqs_v1.py") --stdout-only
    exit $LASTEXITCODE
}

foreach ($j in @($j1, $j2, $j3)) {
    Wait-Job -Job $j | Out-Null
    $out = Receive-Job -Job $j -ErrorAction SilentlyContinue
    $exit = if ($j.ChildJobs.Count -gt 0) { $j.ChildJobs[0].JobStateInfo.Reason } else { $null }
    $ok = ($j.State -eq "Completed")
    $lanes[$j.Name] = @{ ok = $ok; state = $j.State }
    Write-Host ""
    Write-Host "--- $($j.Name) state=$($j.State) ---" -ForegroundColor $(if ($ok) { "Green" } else { "Red" })
    if ($out) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host $_ } }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}

$failed = @($lanes.Keys | Where-Object { -not $lanes[$_].ok })
$doc = @{
    schema           = "next_parallel_lanes_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    lanes            = $lanes
    failed           = $failed
    ok               = ($failed.Count -eq 0)
}
$doc | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ""
Write-Host "Wrote $reportPath ok=$($doc.ok) failed=$($failed -join ',')" -ForegroundColor $(if ($doc.ok) { "Green" } else { "Yellow" })
exit $(if ($doc.ok) { 0 } else { 1 })
