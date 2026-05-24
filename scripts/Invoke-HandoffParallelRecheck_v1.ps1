#Requires -Version 5.1
<#
.SYNOPSIS
  Handoff block parallel recheck — api, personas, prophecy, Track C, B2B, CF autoverify.
#>
param([string]$WorkspaceRoot = "C:\workspace")

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }

$jobs = @(
    @{
        Name = "api_dns_health"
        Script = {
            param($R, $Py)
            Set-Location $R
            & $Py scripts/ensure_no1kmedi_api_cloudflare_dns_v1.py
            if ($LASTEXITCODE -ne 0) { exit 1 }
            $h = & curl.exe -sS https://api.no1kmedi.com/health 2>&1 | Out-String
            Write-Output $h.Trim()
            if ($h -notmatch '"ok"\s*:\s*true') { exit 2 }
            exit 0
        }
    },
    @{
        Name = "athena_bundle"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmPersonaHealth_v1.ps1 -Persona AthenaBundle
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
        Name = "prophecy_closure"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ProphecyLaneRecommendedClosureBundle_v1.ps1
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "trackc_macro_fusion"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-TrackCMacroDailyFusion_v1.ps1 -SkipGateAlert -SkipExodusSourceFetch
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "trackc_b2b_pack"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-TrackCB2bMeetingPack_v1.ps1
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "cf_autoverify"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-JemaaiShowroomEdgeAutoverify_v1.ps1
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "p0_paths"
        Script = {
            param($R)
            Set-Location $R
            powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_p0_constitution_gate_paths.ps1
            exit $LASTEXITCODE
        }
    }
)

$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
}

$failed = @()
foreach ($h in $handles) {
    $null = Wait-Job -Job $h
    $out = Receive-Job -Job $h -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($h.State -ne "Completed") {
        $failed += $h.Name
        Write-Host "FAIL: $($h.Name) state=$($h.State)" -ForegroundColor Red
    } else {
        Write-Host "OK: $($h.Name)" -ForegroundColor Green
    }
    Remove-Job -Job $h -Force
}

Write-Host ""
Write-Host "==> Post-pass: dashboard + amsaeng (serial)" -ForegroundColor Cyan
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-AmsaengEosaMonitoringBundleTask.ps1 -GovernanceSoftFail | Out-Null

if ($failed.Count -gt 0) {
    Write-Host "FAILED jobs: $($failed -join ', ')" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Handoff parallel recheck complete" -ForegroundColor Green
exit 0
