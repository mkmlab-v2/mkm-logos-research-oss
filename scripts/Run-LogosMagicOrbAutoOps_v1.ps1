# Logos Magic Orb auto ops — gold eval, closure, asset sync, OAuth deploy, KV, probe.
param(
    [switch]$SkipDeploy,
    [switch]$SkipRebuild,
    [switch]$StrictGoldEval
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$out = "reports\logos_magic_orb_auto_ops_v1_latest.json"
$steps = @()
$deployAuthMode = $null

function Step([string]$Name, [scriptblock]$Block) {
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Block
    $code = $LASTEXITCODE
    $script:steps += @{ name = $Name; exit_code = $code }
    if ($code -ne 0) { throw "$Name failed (exit $code)" }
}

Step "deploy-token-readiness" {
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmlifeCfDeployTokenReadiness_v1.ps1 -ApplyIfPresent
}

if (-not $SkipRebuild) {
    foreach ($q in @("q04", "q03", "q01", "q07")) {
        $scriptName = switch ($q) {
            "q04" { "Run-LogosQ04InsightSingle_v1.ps1" }
            "q03" { "Run-LogosQ03InsightSingle_v1.ps1" }
            "q01" { "Run-LogosQ01InsightSingle_v1.ps1" }
            "q07" { "Run-LogosQ07InsightSingle_v1.ps1" }
        }
        Step "insight-$q" {
            powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\$scriptName"
        }
    }
} else {
    Step "gold-eval" {
        $evalArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Run-LogosGoldQueryEval_v1.ps1")
        if ($StrictGoldEval) { $evalArgs += "-Strict" }
        powershell @evalArgs
    }
}

Step "quality-lane-closure" {
    $closureArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Run-LogosMagicOrbQualityLaneClosure_v1.ps1")
    if ($StrictGoldEval) { $closureArgs += "-StrictGoldEval" }
    powershell @closureArgs
}

$deployOk = $null
$kvOk = $null
if (-not $SkipDeploy) {
    Step "sync-open-next-assets" {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-MkmlifeOpenNextMagicOrbAssets_v1.ps1
    }

    $envFile = Join-Path (Get-Location) ".env"
    if (Test-Path -LiteralPath $envFile) {
        Get-Content -LiteralPath $envFile | ForEach-Object {
            if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$' -and -not $_.TrimStart().StartsWith("#")) {
                $name = $Matches[1]
                $val = $Matches[2].Trim().Trim('"').Trim("'")
                if ($name -in @("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "MKM_MKMLIFE_CF_DEPLOY_TOKEN", "MKM_MAGIC_ORB_INSIGHT_WEBHOOK_TOKEN")) {
                    Set-Item -Path "Env:$name" -Value $val
                }
            }
        }
    }
    $null = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1
    if (($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 2) -and $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN) {
        $env:CLOUDFLARE_API_TOKEN = $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN
        $env:MKM_WRANGLER_FORCE_API_TOKEN = "1"
        $script:deployAuthMode = "deploy_token"
        Write-Host "[auto-ops] using MKM_MKMLIFE_CF_DEPLOY_TOKEN (Workers+KV probe OK)" -ForegroundColor DarkGray
    } else {
        Remove-Item Env:MKM_WRANGLER_FORCE_API_TOKEN -ErrorAction SilentlyContinue
        Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
        Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
        $script:deployAuthMode = "wrangler_oauth"
        Write-Host "[auto-ops] wrangler OAuth fallback (deploy token probe failed or missing)" -ForegroundColor DarkGray
    }

    Step "mkmlife-deploy-skipbuild" {
        powershell -NoProfile -ExecutionPolicy Bypass -File projects\mkm\mkm-life\scripts\Deploy-CloudflareMkmlife.ps1 -SkipOracleSphereHero -SkipBuild
    }
    $deployOk = $true

    Step "mkmlife-kv-insight-push" {
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1 -WranglerDirect
    }
    $kvOk = $true
}

Step "live-probe" {
    py scripts/probe_mkmlife_magic_orb_live_v1.py
}

$closure = Get-Content "reports\logos_magic_orb_quality_lane_closure_v1_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$readiness = Get-Content "reports\mkmlife_cf_deploy_token_readiness_v1_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$probe = Get-Content "reports\magic_orb_live_probe_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json

$autoOk = [bool]$closure.closure_ok -and [bool]$probe.all_ok -and ($(if ($SkipDeploy) { $true } else { $deployOk -and $kvOk }))

@{
    schema = "logos_magic_orb_auto_ops_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tier = "B"
    research_only = $true
    non_gating = $true
    auto_ok = $autoOk
    skip_rebuild = [bool]$SkipRebuild
    skip_deploy = [bool]$SkipDeploy
    deploy_token_ready = [bool]$readiness.deploy_token_ready
    deploy_auth_mode = $deployAuthMode
    closure_ok = [bool]$closure.closure_ok
    probe_all_ok = [bool]$probe.all_ok
    deploy_ok = $deployOk
    kv_ok = $kvOk
    steps = $steps
} | ConvertTo-Json -Depth 8 | Set-Content -Path $out -Encoding UTF8

if ($autoOk) {
    Write-Host "[OK] magic orb auto ops PASS -> $out" -ForegroundColor Green
    exit 0
}
Write-Host "[WARN] magic orb auto ops incomplete -> $out" -ForegroundColor Yellow
exit 1
