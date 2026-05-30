# q04 Magic Orb showroom publish — verify, deploy static, KV (WranglerDirect), live probe.
param(
    [switch]$DryRun,
    [switch]$SkipDeploy,
    [switch]$SkipKv,
    [switch]$SkipSmoke,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$reportPath = "reports\logos_q04_showroom_publish_v1_latest.json"
$q04Hash = "482fb24be6f1ec09"
$q04Public = "projects\mkm\mkm-life\public\data\magic_orb_insight_by_query\$q04Hash.json"
$bridgeMarker = "logos_concept_bridge_gold_q04_judgment_covenant_remnant"
$liveStaticUrl = "https://mkmlife.com/data/magic_orb_insight_by_query/$q04Hash.json"

# Load deploy/KV secrets from repo .env (process scope only).
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

$deploySecret = Join-Path (Get-Location) "reports\cloudflare_mkmlife_deploy_token_secret_LOCAL.json"
if (Test-Path -LiteralPath $deploySecret) {
    $raw = Get-Content -LiteralPath $deploySecret -Raw -Encoding UTF8
    if ($raw -notmatch "PASTE_CF_TOKEN_HERE") {
        Write-Host "[q04] applying mkmlife deploy token from secret JSON" -ForegroundColor Cyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ApplyMkmlifeCfDeployTokenFromSecret_v1.ps1
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
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
}

$probeExit = & py scripts\_probe_cf_mkmlife_deploy_token_v1.py 2>&1
if (($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 2) -and $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN) {
    $env:CLOUDFLARE_API_TOKEN = $env:MKM_MKMLIFE_CF_DEPLOY_TOKEN
    $env:MKM_WRANGLER_FORCE_API_TOKEN = "1"
    Write-Host "[q04] using MKM_MKMLIFE_CF_DEPLOY_TOKEN (Workers+KV probe OK)" -ForegroundColor DarkGray
} else {
    Remove-Item Env:MKM_WRANGLER_FORCE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
    Write-Host "[q04] wrangler OAuth preferred (analytics-only CLOUDFLARE_API_TOKEN cleared)" -ForegroundColor DarkGray
}

$status = @{
    schema = "logos_q04_showroom_publish_v1"
    query_id = "q04"
    query_key_hash = $q04Hash
    deploy_ok = $null
    kv_ok = $null
    live_static_bridge_ok = $null
    probe_ok = $null
    blockers = @()
}

& py scripts/verify_magic_orb_graph_bloom_assets_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path -LiteralPath $q04Public)) {
    Write-Error "Missing q04 public asset: $q04Public — run Run-LogosQ04InsightSingle_v1.ps1 first"
}

if ($SkipBuild -and -not $SkipDeploy -and -not $DryRun) {
    Write-Host "[q04] syncing public -> .open-next/assets (SkipBuild)" -ForegroundColor DarkGray
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Sync-MkmlifeOpenNextMagicOrbAssets_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipDeploy) {
    if ($DryRun) {
        Write-Host "[DRY] Deploy-CloudflareMkmlife.ps1 -SkipOracleSphereHero" -ForegroundColor Yellow
        $status.deploy_ok = $true
    } else {
        $deployArgs = @(
            "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", "projects\mkm\mkm-life\scripts\Deploy-CloudflareMkmlife.ps1",
            "-SkipOracleSphereHero"
        )
        if ($SkipBuild) { $deployArgs += "-SkipBuild" }
        & powershell @deployArgs
        $status.deploy_ok = ($LASTEXITCODE -eq 0)
        if (-not $status.deploy_ok) {
            $status.blockers += "wrangler deploy/KV auth failed (CLOUDFLARE_API_TOKEN scope or wrangler login expired)"
        }
    }
} else {
    $status.deploy_ok = $true
}

if (-not $DryRun -and $status.deploy_ok -and -not $SkipDeploy) {
    # Deploy script may return 0 even when wrangler steps fail; verify live asset.
    $localHasBridge = (Get-Content -LiteralPath $q04Public -Raw) -match [regex]::Escape($bridgeMarker)
    if ($localHasBridge) { $status.deploy_ok = $null }
}

if (-not $SkipKv) {
    if ($DryRun) {
        Write-Host "[DRY] Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1 -WranglerDirect" -ForegroundColor Yellow
        $status.kv_ok = $true
    } else {
        $kvArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1", "-WranglerDirect")
        & powershell @kvArgs
        $status.kv_ok = ($LASTEXITCODE -eq 0)
        if (-not $status.kv_ok) {
            Write-Host "[q04] wrangler KV failed; retry via live webhook POST" -ForegroundColor Yellow
            & py scripts/push_magic_orb_insight_webhook_v1.py --base-url https://mkmlife.com --push-all-by-query
            $wh1 = $LASTEXITCODE
            & py scripts/push_magic_orb_insight_webhook_v1.py --base-url https://mkmlife.com
            $wh2 = $LASTEXITCODE
            if ($wh1 -eq 0 -and $wh2 -eq 0) {
                $status.kv_ok = $true
            } else {
                $status.blockers += "webhook KV warm failed (HTTP 403/1010, CF edge or token)"
            }
        }
    }
} else {
    $status.kv_ok = $true
}

if (-not $DryRun) {
    $verifyJson = (& py -3 -c "import json,urllib.request; from pathlib import Path; local=Path(r'$q04Public').read_text(encoding='utf-8'); live_ok=False
try:
 import urllib.request
 live_ok='$bridgeMarker' in urllib.request.urlopen('$liveStaticUrl',timeout=25).read().decode('utf-8','replace')
except Exception: pass
print(json.dumps({'local_bridge_ok':'$bridgeMarker' in local,'live_bridge_ok':live_ok}))")
    $verify = $verifyJson | ConvertFrom-Json
    $status.live_static_bridge_ok = [bool]$verify.live_bridge_ok
    if (-not $status.live_static_bridge_ok) {
        $status.blockers += "live static missing q04 judgment/covenant bridge; redeploy after CF auth fix"
        if (-not $SkipDeploy) { $status.deploy_ok = $false }
    } elseif ($null -eq $status.deploy_ok) {
        $status.deploy_ok = $true
    }
}

if (-not $SkipSmoke) {
    if ($DryRun) {
        Write-Host "[DRY] probe_mkmlife_magic_orb_live_v1.py" -ForegroundColor Yellow
        $status.probe_ok = $true
    } else {
        & py scripts/probe_mkmlife_magic_orb_live_v1.py
        $status.probe_ok = ($LASTEXITCODE -eq 0)
    }
}

$status.generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$status.publish_complete = ($status.deploy_ok -and $status.kv_ok -and $status.live_static_bridge_ok)
$status | ConvertTo-Json -Depth 6 | Set-Content -Path $reportPath -Encoding UTF8

if ($status.publish_complete) {
    Write-Host "[OK] q04 showroom publish complete ($reportPath)" -ForegroundColor Green
    exit 0
}

Write-Host "[PARTIAL] q04 publish blocked — see $reportPath" -ForegroundColor Yellow
foreach ($b in $status.blockers) { Write-Host "  - $b" -ForegroundColor Yellow }
Write-Host "Fix: projects\mkm\mkm-life 에서 npx wrangler login 후 본 스크립트 재실행 (또는 CF 토큰에 Workers Scripts Edit + Workers KV Storage Edit)" -ForegroundColor Cyan
exit 1
