# q08 Magic Orb showroom publish — verify, deploy static, KV (WranglerDirect), live probe.
param(
    [switch]$DryRun,
    [switch]$SkipDeploy,
    [switch]$SkipKv,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

# Prefer wrangler OAuth over analytics-only CLOUDFLARE_API_TOKEN (see Run-LogosQ04ShowroomPublish_v1.ps1).
$envFile = Join-Path (Get-Location) ".env"
if (Test-Path -LiteralPath $envFile) {
    Get-Content -LiteralPath $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$' -and -not $_.TrimStart().StartsWith("#")) {
            $name = $Matches[1]
            $val = $Matches[2].Trim().Trim('"').Trim("'")
            if ($name -in @("MKM_MKMLIFE_CF_DEPLOY_TOKEN", "MKM_MAGIC_ORB_INSIGHT_WEBHOOK_TOKEN")) {
                Set-Item -Path "Env:$name" -Value $val
            }
        }
    }
}
$probeExit = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1
if (($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 2) -and $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN) {
    $env:CLOUDFLARE_API_TOKEN = $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN
    $env:MKM_WRANGLER_FORCE_API_TOKEN = "1"
} else {
    Remove-Item Env:MKM_WRANGLER_FORCE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
}

& py scripts/verify_magic_orb_graph_bloom_assets_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$q08Public = "projects\mkm\mkm-life\public\data\magic_orb_insight_by_query\23524432377849f7.json"
if (-not (Test-Path -LiteralPath $q08Public)) {
    Write-Error "Missing q08 public asset: $q08Public — run Run-LogosQ08InsightSingle_v1.ps1 first"
}

if (-not $SkipDeploy) {
    if ($DryRun) {
        Write-Host "[DRY] Deploy-CloudflareMkmlife.ps1 -SkipOracleSphereHero" -ForegroundColor Yellow
    } else {
        $deployArgs = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", "projects\mkm\mkm-life\scripts\Deploy-CloudflareMkmlife.ps1",
            "-SkipOracleSphereHero"
        )
        & powershell @deployArgs
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

if (-not $SkipKv) {
    $kvArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1", "-WranglerDirect")
    if ($DryRun) { $kvArgs += "-DryRun" }
    & powershell @kvArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipSmoke) {
    if ($DryRun) {
        Write-Host "[DRY] probe_mkmlife_magic_orb_live_v1.py" -ForegroundColor Yellow
    } else {
        & py scripts/probe_mkmlife_magic_orb_live_v1.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

Write-Host "[OK] q08 showroom publish path complete" -ForegroundColor Green
