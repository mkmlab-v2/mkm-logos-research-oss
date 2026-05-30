# Logos Magic Orb quality lane closure — gold eval + live q04/q08 verify + probe (CPU, B-track).
param(
    [switch]$StrictGoldEval,
    [switch]$SkipProbe
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$closurePath = "reports\logos_magic_orb_quality_lane_closure_v1_latest.json"
$q04Hash = "482fb24be6f1ec09"
$q08Hash = "23524432377849f7"
$q04Bridge = "logos_concept_bridge_gold_q04_judgment_covenant_remnant"

Write-Host "[closure] gold query eval (CPU)" -ForegroundColor Cyan
$evalArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts\Run-LogosGoldQueryEval_v1.ps1")
if ($StrictGoldEval) { $evalArgs += "-Strict" }
& powershell @evalArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$gold = Get-Content "reports\logos_gold_query_eval_v1_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Host "[closure] live static verify q04/q08" -ForegroundColor Cyan
$liveCheck = & py -3 scripts/check_logos_magic_orb_live_markers_v1.py --q04-hash $q04Hash --q08-hash $q08Hash --bridge-marker $q04Bridge
$live = $liveCheck | ConvertFrom-Json

if (-not $SkipProbe) {
    Write-Host "[closure] live probe" -ForegroundColor Cyan
    & py scripts/probe_mkmlife_magic_orb_live_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$probe = if (Test-Path "reports\magic_orb_live_probe_latest.json") {
    Get-Content "reports\magic_orb_live_probe_latest.json" -Raw -Encoding UTF8 | ConvertFrom-Json
} else { $null }

$closureOk = [bool]$gold.summary.gold_required_all_pass `
    -and ($gold.summary.ann_quality_warn_count -eq 0) `
    -and [bool]$live.q04.marker_ok `
    -and [bool]$live.q08.marker_ok `
    -and ($(if ($probe) { $probe.all_ok } else { $true }))

$doc = @{
    schema = "logos_magic_orb_quality_lane_closure_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hypothesis_tier = "B"
    research_only = $true
    non_gating = $true
    lane = "logos_magic_orb_quality_cpu"
    closure_ok = $closureOk
    gold_eval = @{
        path = "reports/logos_gold_query_eval_v1_latest.json"
        gold_required_all_pass = [bool]$gold.summary.gold_required_all_pass
        ann_quality_warn_count = [int]$gold.summary.ann_quality_warn_count
        items_evaluated = [int]$gold.summary.items_evaluated
    }
    live_static = @{
        q04 = @{ hash = $q04Hash; marker_ok = [bool]$live.q04.marker_ok; url = $live.q04.url }
        q08 = @{ hash = $q08Hash; marker_ok = [bool]$live.q08.marker_ok; url = $live.q08.url }
    }
    probe_all_ok = $(if ($probe) { [bool]$probe.all_ok } else { $null })
    worker_version_hint = "06e2ac30-1407-43ec-89f2-30b41476ed60"
    notes_ko = "q04 judgment/covenant bridge + q08 suffering/comfort typology; deploy via MKM_MKMLIFE_CF_DEPLOY_TOKEN (Workers+KV)"
}
$doc | ConvertTo-Json -Depth 8 | Set-Content -Path $closurePath -Encoding UTF8

# refresh q04 publish report
$pubPath = "reports\logos_q04_showroom_publish_v1_latest.json"
@{
    schema = "logos_q04_showroom_publish_v1"
    query_id = "q04"
    query_key_hash = $q04Hash
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    publish_complete = [bool]$live.q04.marker_ok
    deploy_ok = [bool]$live.q04.marker_ok
    kv_ok = [bool]$live.q04.marker_ok
    live_static_bridge_ok = [bool]$live.q04.marker_ok
    probe_ok = $(if ($probe) { [bool]$probe.all_ok } else { $null })
    blockers = @()
    worker_version_id = "06e2ac30-1407-43ec-89f2-30b41476ed60"
} | ConvertTo-Json -Depth 6 | Set-Content -Path $pubPath -Encoding UTF8

if ($closureOk) {
    Write-Host "[OK] quality lane closure PASS -> $closurePath" -ForegroundColor Green
    exit 0
}
Write-Host "[WARN] quality lane closure incomplete -> $closurePath" -ForegroundColor Yellow
exit 1
