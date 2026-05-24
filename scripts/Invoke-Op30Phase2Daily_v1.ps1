#Requires -Version 5.1
<#
.SYNOPSIS
  O-P30 Phase 2 daily: refresh envelope, optional CF asset deploy, live probe.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DeployAssets,
    [switch]$FullDeploy,
    [switch]$SkipProbe,
    [switch]$IncludeLivePatrol
)

$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$reportPath = Join-Path $WorkspaceRoot "reports\op30_phase2_daily_latest.json"
$failed = @()

Write-Host "==> envelope assemble" -ForegroundColor Cyan
& $py scripts/assemble_three_lens_sphere_envelope_v1.py --validate-schema --copy-mkmlife-public
if ($LASTEXITCODE -ne 0) { $failed += "envelope" }

$src = Join-Path $WorkspaceRoot "projects\mkm\mkm-life\public\data\three_lens_sphere_envelope_v1.json"
$assetDir = Join-Path $WorkspaceRoot "projects\mkm\mkm-life\.open-next\assets\data"
if (Test-Path $src) {
    New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
    Copy-Item -LiteralPath $src -Destination (Join-Path $assetDir "three_lens_sphere_envelope_v1.json") -Force
    Write-Host "Synced envelope -> .open-next/assets/data/" -ForegroundColor DarkGray
}

$mkmlifeRoot = Join-Path $WorkspaceRoot "projects\mkm\mkm-life"
if ($FullDeploy) {
    Write-Host "==> mkmlife full deploy (worker patches)" -ForegroundColor Cyan
    Push-Location $mkmlifeRoot
    try {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Deploy-CloudflareMkmlife.ps1
        if ($LASTEXITCODE -ne 0) { $failed += "full_deploy" }
    } finally { Pop-Location }
} elseif ($DeployAssets) {
    Write-Host "==> mkmlife asset-only wrangler deploy" -ForegroundColor Cyan
    $worker = Join-Path $mkmlifeRoot ".open-next\worker.js"
    if (-not (Test-Path $worker)) {
        Write-Host "WARN: .open-next missing — run -FullDeploy once" -ForegroundColor Yellow
        $failed += "asset_deploy_skipped"
    } else {
        Push-Location $mkmlifeRoot
        try {
            Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
            Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
            npx wrangler deploy --config wrangler.jsonc
            if ($LASTEXITCODE -ne 0) { $failed += "asset_deploy" }
        } finally { Pop-Location }
    }
}

if ($IncludeLivePatrol) {
    Write-Host "==> LivePatrol" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-LivePatrolDaily_v1.ps1
    if ($LASTEXITCODE -ne 0) { $failed += "live_patrol" }
}

$probeOk = $true
if (-not $SkipProbe) {
    Write-Host "==> live probe" -ForegroundColor Cyan
    & $py scripts/probe_mkmlife_magic_orb_live_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "probe"; $probeOk = $false }
    & $py scripts/probe_mkmlife_cf_traffic_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "cf_traffic_probe" }
    & $py scripts/build_magic_orb_open_beta_traffic_summary_v1.py
    if ($LASTEXITCODE -ne 0) { $failed += "traffic_summary" }
}

$envPath = Join-Path $WorkspaceRoot "docs\final\artifacts\three_lens_sphere_envelope_v1_latest.json"
$finalAction = $null
if (Test-Path $envPath) {
    $finalAction = (Get-Content -LiteralPath $envPath -Raw -Encoding UTF8 | ConvertFrom-Json).final_action
}

[ordered]@{
    schema = "op30_phase2_daily_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    failed_steps = @($failed)
    envelope_final_action = $finalAction
    deploy_assets = $DeployAssets.IsPresent
    full_deploy = $FullDeploy.IsPresent
    probe_ok = $probeOk
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host "Wrote $reportPath failed=$($failed.Count)" -ForegroundColor $(if ($failed.Count -eq 0) { "Green" } else { "Yellow" })
if ($failed.Count -gt 0) { exit 1 }
exit 0
