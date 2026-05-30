# Gold Magic Orb showroom publish (q04–q08 default) — deploy static + KV + live probe.
param(
    [string[]]$QueryIds = @("q01", "q02", "q03", "q04", "q05", "q06", "q07", "q08"),
    [switch]$DryRun,
    [switch]$SkipDeploy,
    [switch]$SkipKv,
    [switch]$SkipSmoke,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

# Normalize QueryIds when passed as a single comma-separated string from CLI.
if ($QueryIds.Count -eq 1 -and $QueryIds[0] -match ',') {
    $QueryIds = $QueryIds[0].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

$reportPath = "reports\logos_gold_showroom_publish_v1_latest.json"
$fixturePath = "docs\final\fixtures\magic_orb_question_insight_queries_v1.json"
$publicDir = "projects\mkm\mkm-life\public\data\magic_orb_insight_by_query"

function Get-QueryHash16([string]$Query) {
    $norm = ($Query.Trim() -replace '\s+', ' ')
    if ($norm.Length -gt 800) { $norm = $norm.Substring(0, 800) }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($norm)
    $hash = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ''
    return $hash.Substring(0, 16)
}

$fixture = Get-Content -LiteralPath $fixturePath -Raw -Encoding UTF8 | ConvertFrom-Json
$rows = @()
foreach ($qid in $QueryIds) {
    $qid = ($qid -replace '^"|"$', '').Trim()
    $item = $fixture.items | Where-Object { $_.id -eq $qid } | Select-Object -First 1
    if (-not $item) { Write-Error "Missing fixture row for $qid" }
    $hh = Get-QueryHash16 $item.query_ko
    $pub = Join-Path $publicDir "$hh.json"
    if (-not (Test-Path -LiteralPath $pub)) {
        Write-Error "Missing public asset for ${qid}: $pub — run Run-LogosGoldBatchInsight_v1.ps1 first"
    }
    $doc = Get-Content -LiteralPath $pub -Raw -Encoding UTF8 | ConvertFrom-Json
    $nodes = @($doc.graph_bloom.nodes).Count
    if ($nodes -ne 64) {
        Write-Error "${qid} public bloom has nodes=$nodes (expected 64)"
    }
    $rows += [ordered]@{
        query_id = $qid
        query_key_hash = $hh
        public_path = $pub
        bloom_nodes = $nodes
    }
}

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
        Write-Host "[gold] applying mkmlife deploy token from secret JSON" -ForegroundColor Cyan
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
    Write-Host "[gold] using MKM_MKMLIFE_CF_DEPLOY_TOKEN (Workers+KV probe OK)" -ForegroundColor DarkGray
} else {
    Remove-Item Env:MKM_WRANGLER_FORCE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:CF_API_TOKEN -ErrorAction SilentlyContinue
    Write-Host "[gold] wrangler OAuth preferred (analytics-only CLOUDFLARE_API_TOKEN cleared)" -ForegroundColor DarkGray
}

$status = @{
    schema = "logos_gold_showroom_publish_v1"
    query_ids = @($QueryIds)
    rows = $rows
    deploy_ok = $null
    kv_ok = $null
    live_static_ok = $null
    probe_ok = $null
    blockers = @()
}

& py scripts/verify_magic_orb_graph_bloom_assets_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipBuild -and -not $SkipDeploy -and -not $DryRun) {
    Write-Host "[gold] syncing public -> .open-next/assets (SkipBuild)" -ForegroundColor DarkGray
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

if (-not $SkipKv) {
    if ($DryRun) {
        Write-Host "[DRY] Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1 -WranglerDirect" -ForegroundColor Yellow
        $status.kv_ok = $true
    } else {
        $kvArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1", "-WranglerDirect")
        & powershell @kvArgs
        $status.kv_ok = ($LASTEXITCODE -eq 0)
        if (-not $status.kv_ok) {
            Write-Host "[gold] wrangler KV failed; retry via live webhook POST" -ForegroundColor Yellow
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
    $liveOk = $true
    foreach ($row in $rows) {
        $url = "https://mkmlife.com/data/magic_orb_insight_by_query/$($row.query_key_hash).json"
        try {
            $live = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 25).Content | ConvertFrom-Json
            $ln = @($live.graph_bloom.nodes).Count
            if ($ln -ne 64) {
                $liveOk = $false
                $status.blockers += "live static $($row.query_id) nodes=$ln (expected 64) url=$url"
            }
        } catch {
            $liveOk = $false
            $status.blockers += "live static fetch failed $($row.query_id): $($_.Exception.Message)"
        }
    }
    $status.live_static_ok = $liveOk
    if (-not $liveOk -and -not $SkipDeploy) { $status.deploy_ok = $false }
}

if (-not $SkipSmoke) {
    if ($DryRun) {
        Write-Host "[DRY] _auto_verify_oracle_sphere_showroom_v1.py" -ForegroundColor Yellow
        $status.probe_ok = $true
    } else {
        & py scripts/_auto_verify_oracle_sphere_showroom_v1.py
        $status.probe_ok = ($LASTEXITCODE -eq 0)
    }
}

$status.generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$status.publish_complete = ($status.deploy_ok -and $status.kv_ok -and $status.live_static_ok)
$status | ConvertTo-Json -Depth 8 | Set-Content -Path $reportPath -Encoding UTF8

if ($status.publish_complete) {
    Write-Host "[OK] gold showroom publish complete ($reportPath)" -ForegroundColor Green
    exit 0
}

Write-Host "[PARTIAL] gold publish blocked — see $reportPath" -ForegroundColor Yellow
foreach ($b in $status.blockers) { Write-Host "  - $b" -ForegroundColor Yellow }
Write-Host "Fix: run npx wrangler login in projects/mkm/mkm-life then re-run this script" -ForegroundColor Cyan
exit 1
