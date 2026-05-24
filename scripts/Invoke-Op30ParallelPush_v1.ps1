#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 + 운영 병렬: envelope assemble, patrol, oracle omni, prophecy chain, showroom, dashboard.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipLivePatrol,
    [switch]$SkipProphecySweep,
    [switch]$SkipOracleOmni
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$reportPath = Join-Path $WorkspaceRoot "reports\op30_parallel_push_latest.json"

$jobs = @(
    @{
        Name = "op30_envelope"
        Script = {
            param($R, $Py)
            Set-Location $R
            & $Py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema --copy-mkmlife-public
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "prophecy_closure"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1 -AllowDisabledSecurityIntegrityTask
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "showroom_health"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona ShowroomTrackCHealth
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "compression_kpi"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_compression_automation_chain.ps1
            exit $LASTEXITCODE
        }
    }
)

if (-not $SkipLivePatrol) {
    $jobs = @(@{
            Name = "live_patrol"
            Script = {
                param($R)
                Set-Location $R
                powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LivePatrolDaily_v1.ps1
                exit $LASTEXITCODE
            }
        }) + $jobs
}

if (-not $SkipProphecySweep) {
    $jobs += @{
        Name = "prophecy_recommended_chain"
        Script = {
            param($R, $Py)
            Set-Location $R
            & $Py scripts/run_prophecy_btrack_recommended_eval_chain_v1.py
            exit $LASTEXITCODE
        }
    }
}

if (-not $SkipOracleOmni) {
    $jobs += @{
        Name = "oracle_omni"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosOracleOmniParallel_v1.ps1 -MirrorShowroomCdim
            exit $LASTEXITCODE
        }
    }
}

$failed = @()
$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
}
$null = Wait-Job $handles
foreach ($h in $handles) {
    $out = Receive-Job $h -ErrorAction SilentlyContinue
    if ($h.State -ne "Completed") { $failed += $h.Name }
    $code = if ($h.ChildJobs.Count -gt 0) { $h.ChildJobs[0].JobStateInfo.Reason } else { $null }
    Write-Host "--- $($h.Name) $($h.State) ---" -ForegroundColor $(if ($h.State -eq "Completed") { "Green" } else { "Yellow" })
    if ($out) { @($out)[-8..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    Remove-Job $h -Force
}

Write-Host "`n==> Serial tail" -ForegroundColor Cyan
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "trackc_dashboard" }

$envPath = Join-Path $WorkspaceRoot "docs\final\artifacts\three_lens_sphere_envelope_v1_latest.json"
$envDoc = $null
if (Test-Path $envPath) {
    $envDoc = Get-Content -LiteralPath $envPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$rollup = [ordered]@{
    schema = "op30_parallel_push_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_jobs = @($failed)
    envelope_final_action = $envDoc.final_action
    envelope_path = "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
    mkmlife_public = "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_v1.json"
}
$rollup | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "Wrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
