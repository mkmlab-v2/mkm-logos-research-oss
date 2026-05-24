#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 Phase3 병렬: 운영(예언·쇼룸·압축·파수) + 오픈베타 readiness + envelope → asset deploy + probe.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipLivePatrol,
    [switch]$SkipProphecySweep,
    [switch]$SkipOracleOmni,
    [switch]$SkipAssetDeploy
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$reportPath = Join-Path $WorkspaceRoot "reports\op30_phase3_parallel_latest.json"
$failed = @()

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
        Name = "section11_readiness"
        Script = {
            param($R, $Py)
            Set-Location $R
            & $Py scripts/check_mkmlife_section11_readiness_v1.py
            exit $LASTEXITCODE
        }
    },
    @{
        Name = "decoy_d1_readiness"
        Script = {
            param($R, $Py)
            Set-Location $R
            & $Py scripts/check_decoy_d1_mkmlife_readiness_v1.py
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

$handles = @()
foreach ($j in $jobs) {
    Write-Host "Start: $($j.Name)" -ForegroundColor Cyan
    $handles += Start-Job -Name $j.Name -ScriptBlock $j.Script -ArgumentList $WorkspaceRoot, $py
}
$null = Wait-Job $handles
$jobResults = @{}
foreach ($h in $handles) {
    $out = Receive-Job $h -ErrorAction SilentlyContinue
    $ok = ($h.State -eq "Completed")
    $jobResults[$h.Name] = @{ ok = $ok }
    if (-not $ok) { $failed += $h.Name }
    Write-Host "--- $($h.Name) $($h.State) ---" -ForegroundColor $(if ($ok) { "Green" } else { "Yellow" })
    if ($out) { @($out)[-6..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    Remove-Job $h -Force
}

Write-Host "`n==> Serial: asset deploy + probe + dashboard" -ForegroundColor Cyan
$src = Join-Path $WorkspaceRoot "projects\mkm\mkm-life\public\data\three_lens_sphere_envelope_v1.json"
$assetDir = Join-Path $WorkspaceRoot "projects\mkm\mkm-life\.open-next\assets\data"
if (Test-Path $src) {
    New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
    Copy-Item -LiteralPath $src -Destination (Join-Path $assetDir "three_lens_sphere_envelope_v1.json") -Force
}

if (-not $SkipAssetDeploy) {
    $worker = Join-Path $WorkspaceRoot "projects\mkm\mkm-life\.open-next\worker.js"
    if (Test-Path $worker) {
        Push-Location (Join-Path $WorkspaceRoot "projects\mkm\mkm-life")
        try {
            Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
            Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
            npx wrangler deploy --config wrangler.jsonc
            if ($LASTEXITCODE -ne 0) { $failed += "asset_deploy" }
        } finally { Pop-Location }
    } else {
        $failed += "asset_deploy_skipped"
    }
}

& $py scripts/probe_mkmlife_magic_orb_live_v1.py
$probeOk = ($LASTEXITCODE -eq 0)
if (-not $probeOk) { $failed += "live_probe" }

& $py scripts/build_magic_orb_open_beta_traffic_summary_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "traffic_summary" }

& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
if ($LASTEXITCODE -ne 0) { $failed += "trackc_dashboard" }

$section11 = $null
$s11Path = Join-Path $WorkspaceRoot "docs\final\artifacts\mkmlife_section11_readiness_v1_latest.json"
if (Test-Path $s11Path) {
    $section11 = Get-Content -LiteralPath $s11Path -Raw -Encoding UTF8 | ConvertFrom-Json
}
$envPath = Join-Path $WorkspaceRoot "docs\final\artifacts\three_lens_sphere_envelope_v1_latest.json"
$finalAction = $null
if (Test-Path $envPath) {
    $finalAction = (Get-Content -LiteralPath $envPath -Raw -Encoding UTF8 | ConvertFrom-Json).final_action
}

[ordered]@{
    schema = "op30_phase3_parallel_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_steps = @($failed)
    parallel_jobs = $jobResults
    envelope_final_action = $finalAction
    open_beta_section11_ok = $section11.section11_pointer_ok
    payment_e2e_deferred = $section11.payment_e2e_deferred
    live_probe_ok = $probeOk
    phase = "O-P30-Phase3-open-beta"
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "Wrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
