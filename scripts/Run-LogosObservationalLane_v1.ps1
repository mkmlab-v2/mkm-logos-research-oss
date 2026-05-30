# q01+q07 observational lane — typology insight rebuild, gold eval, asset sync, optional deploy.
param(
    [switch]$SkipDeploy,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$reportPath = "reports\logos_observational_lane_v1_latest.json"
$q01Hash = "ac97b7efd98bb326"
$q07Hash = "ac532b47d8664c36"

Write-Host "[obs] q01 primary insight" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosQ01InsightSingle_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[obs] q07 insight" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosQ07InsightSingle_v1.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gold = Get-Content "reports\logos_gold_query_eval_v1_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$q01 = $gold.rows | Where-Object { $_.id -eq "q01" } | Select-Object -First 1
$q07 = $gold.rows | Where-Object { $_.id -eq "q07" } | Select-Object -First 1

$deployOk = $null
if (-not $SkipDeploy) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-MkmlifeOpenNextMagicOrbAssets_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Remove-Item Env:MKM_WRANGLER_FORCE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue

    $deployArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", "projects\mkm\mkm-life\scripts\Deploy-CloudflareMkmlife.ps1",
        "-SkipOracleSphereHero"
    )
    if ($SkipBuild) { $deployArgs += "-SkipBuild" }
    & powershell @deployArgs
    $deployOk = ($LASTEXITCODE -eq 0)
    if ($deployOk) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1 -WranglerDirect
        if ($LASTEXITCODE -ne 0) { $deployOk = $false }
    }
}

& py scripts/probe_mkmlife_magic_orb_live_v1.py
$probeOk = ($LASTEXITCODE -eq 0)

@{
    schema = "logos_observational_lane_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tier = "B"
    research_only = $true
    non_gating = $true
    q01 = @{
        hash = $q01Hash
        ann_typology = [bool]$q01.ann_lite.typology_boost_applied
        ann_hit_at_1 = [bool]$q01.hit_at_k.'1'.ann
        ann_hit_at_8 = [bool]$q01.hit_at_k.'8'.ann
    }
    q07 = @{
        hash = $q07Hash
        ann_typology = [bool]$q07.ann_lite.typology_boost_applied
        ann_hit_at_1 = [bool]$q07.hit_at_k.'1'.ann
        ann_hit_at_8 = [bool]$q07.hit_at_k.'8'.ann
    }
    gold_required_all_pass = [bool]$gold.summary.gold_required_all_pass
    deploy_ok = $deployOk
    probe_all_ok = [bool]$probeOk
} | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8

Write-Host "[OK] observational lane -> $reportPath" -ForegroundColor Green
