# q02+q05 observational lane — typology insight rebuild, gold eval, optional deploy.

param(

    [switch]$SkipDeploy,

    [switch]$SkipBuild

)



$ErrorActionPreference = "Stop"

Set-Location "C:\workspace"



$reportPath = "reports\logos_q02_q05_observational_lane_v1_latest.json"

$q02Hash = "e8ac9e70c843d1e6"

$q05Hash = "5d940bba424da73b"



Write-Host "[obs-q02q05] q02 insight" -ForegroundColor Cyan

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosQ02InsightSingle_v1.ps1

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



Write-Host "[obs-q02q05] q05 insight" -ForegroundColor Cyan

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-LogosQ05InsightSingle_v1.ps1

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



$gold = Get-Content "reports\logos_gold_query_eval_v1_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json

$q02 = $gold.rows | Where-Object { $_.id -eq "q02" } | Select-Object -First 1

$q05 = $gold.rows | Where-Object { $_.id -eq "q05" } | Select-Object -First 1



$deployOk = $null

if (-not $SkipDeploy) {

    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-MkmlifeOpenNextMagicOrbAssets_v1.ps1

    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }



    $envFile = Join-Path (Get-Location) ".env"

    if (Test-Path -LiteralPath $envFile) {

        Get-Content -LiteralPath $envFile | ForEach-Object {

            if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$' -and -not $_.TrimStart().StartsWith("#")) {

                $name = $Matches[1]

                $val = $Matches[2].Trim().Trim('"').Trim("'")

                if ($name -in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "MKM_MKMLIFE_CF_DEPLOY_TOKEN")) {

                    Set-Item -Path "Env:$name" -Value $val

                }

            }

        }

    }

    $null = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1

    if (($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 2) -and $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN) {

        $env:CLOUDFLARE_API_TOKEN = $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN

        $env:MKM_WRANGLER_FORCE_API_TOKEN = "1"

    } else {

        Remove-Item Env:MKM_WRANGLER_FORCE_API_TOKEN -ErrorAction SilentlyContinue

        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue

    }



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

    schema = "logos_q02_q05_observational_lane_v1"

    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    hypothesis_tier = "B"

    research_only = $true

    non_gating = $true

    q02 = @{

        hash = $q02Hash

        ann_typology = [bool]$q02.ann_lite.typology_boost_applied

        ann_hit_at_1 = [bool]$q02.hit_at_k.'1'.ann

        ann_hit_at_8 = [bool]$q02.hit_at_k.'8'.ann

    }

    q05 = @{

        hash = $q05Hash

        ann_typology = [bool]$q05.ann_lite.typology_boost_applied

        ann_hit_at_1 = [bool]$q05.hit_at_k.'1'.ann

        ann_hit_at_8 = [bool]$q05.hit_at_k.'8'.ann

    }

    gold_required_all_pass = [bool]$gold.summary.gold_required_all_pass

    items_evaluated = [int]$gold.summary.items_evaluated

    deploy_ok = $deployOk

    probe_all_ok = [bool]$probeOk

} | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8



Write-Host "[OK] q02/q05 observational lane -> $reportPath" -ForegroundColor Green

