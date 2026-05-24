#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 Phase 1: envelope refresh, mkmlife OpenNext build+deploy, jemaai v6 hub CTA, showroom VPS sync.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMkmlifeDeploy,
    [switch]$SkipShowroomSync,
    [switch]$SkipLivePatrol
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$reportPath = Join-Path $WorkspaceRoot "reports\op30_phase1_push_latest.json"
$failed = @()
$steps = [ordered]@{}

function Step-Run {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    try {
        & $Block
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        $steps[$Name] = @{ exit_code = $code; ok = ($code -eq 0) }
        if ($code -ne 0) { $script:failed += $Name }
        return $code
    } catch {
        $steps[$Name] = @{ exit_code = 1; ok = $false; error = $_.Exception.Message }
        $script:failed += $Name
        return 1
    }
}

# Parallel wave A
$waveA = @()
$waveA += Start-Job -Name "envelope" -ScriptBlock {
    param($R, $Py)
    Set-Location $R
    & $Py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema --copy-mkmlife-public
    exit $LASTEXITCODE
} -ArgumentList $WorkspaceRoot, $py

$waveA += Start-Job -Name "showroom_staging" -ScriptBlock {
    param($R)
    Set-Location (Join-Path $R "projects\bitcoin-trading\ops\windows-rehearsal")
    if (Test-Path ".\deploy_showroom_static.ps1") {
        powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy_showroom_static.ps1
        exit $LASTEXITCODE
    }
    exit 0
} -ArgumentList $WorkspaceRoot

if (-not $SkipLivePatrol) {
    $waveA += Start-Job -Name "live_patrol" -ScriptBlock {
        param($R)
        Set-Location $R
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LivePatrolDaily_v1.ps1
        exit $LASTEXITCODE
    } -ArgumentList $WorkspaceRoot
}

$null = Wait-Job $waveA
foreach ($j in $waveA) {
    $out = Receive-Job $j -ErrorAction SilentlyContinue
    $ok = ($j.State -eq "Completed")
    $steps[$j.Name] = @{ ok = $ok }
    if (-not $ok) { $failed += $j.Name }
    Write-Host "--- $($j.Name) $($j.State) ---" -ForegroundColor $(if ($ok) { "Green" } else { "Yellow" })
    if ($out) { @($out)[-6..-1] | Where-Object { $_ } | ForEach-Object { Write-Host $_ } }
    Remove-Job $j -Force
}

# mkmlife build+deploy (serial — heavy). Full Deploy applies worker patches (www redirect, chdir).
$mkmlifeRoot = Join-Path $WorkspaceRoot "projects\mkm\mkm-life"
if (-not $SkipMkmlifeDeploy) {
    Step-Run "mkmlife_cloudflare_deploy" {
        Set-Location $mkmlifeRoot
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Deploy-CloudflareMkmlife.ps1
    } | Out-Null
} else {
    Step-Run "mkmlife_opennext_build" {
        Set-Location $mkmlifeRoot
        npx opennextjs-cloudflare build
    } | Out-Null
    $steps["mkmlife_cloudflare_deploy"] = @{ ok = $true; skipped = $true }
}

if (-not $SkipShowroomSync) {
    Step-Run "showroom_vps_sync" {
        Set-Location $WorkspaceRoot
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\sync_showroom_to_vps.ps1 -RefreshStaging
    } | Out-Null
}

# Verify
$verify = @{}
$urls = @(
    "https://mkmlife.com/oracle-sphere",
    "https://mkmlife.com/data/three_lens_sphere_envelope_v1.json",
    "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"
)
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $u -Method Head -UseBasicParsing -TimeoutSec 25
        $verify[$u] = @{ status = [int]$r.StatusCode; ok = ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) }
    } catch {
        $verify[$u] = @{ ok = $false; error = $_.Exception.Message }
    }
}

$envPath = Join-Path $WorkspaceRoot "docs\final\artifacts\three_lens_sphere_envelope_v1_latest.json"
$envDoc = $null
if (Test-Path $envPath) {
    $envDoc = Get-Content -LiteralPath $envPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$rollup = [ordered]@{
    schema = "op30_phase1_push_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_steps = @($failed)
    steps = $steps
    verify = $verify
    envelope_final_action = $envDoc.final_action
    envelope_path = "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
}
$rollup | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host "`nWrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
