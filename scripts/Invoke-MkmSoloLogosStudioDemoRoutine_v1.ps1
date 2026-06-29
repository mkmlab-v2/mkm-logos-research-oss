# 1인 개발자 — Logos Studio 데모 루틴 (KOSPI 유지보수 + sync + smoke + WTP readiness)
param(
    [string]$WorkspaceRoot = "",
    [string]$SmokeBase = "https://logos.jema-ai.com",
    [switch]$SkipKospiMaintenance,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) {
    $WorkspaceRoot.TrimEnd('\', '/')
} elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $root

$out = Join-Path $root "reports/mkm_solo_logos_studio_demo_routine_v1_latest.json"
$no1k = Join-Path $root "projects/no1kmedi"
$steps = [System.Collections.Generic.List[object]]::new()

function Invoke-Step {
    param([string]$Id, [scriptblock]$Body)
    if ($WhatIf) {
        Write-Host "[solo-logos-demo] plan: $Id"
        return @{ id = $Id; ok = $true; skipped = $true }
    }
    Write-Host "[solo-logos-demo] $Id"
    $code = 0
    $detail = $null
    try {
        & $Body
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
    } catch {
        $code = 1
        $detail = $_.Exception.Message
    }
    $ok = $code -eq 0
    $row = @{ id = $Id; ok = $ok; exit_code = $code }
    if ($detail) { $row.detail = $detail }
    $steps.Add([pscustomobject]$row) | Out-Null
    return $row
}

if (-not $SkipKospiMaintenance) {
    Invoke-Step "kospi_followup_chain" {
        & py (Join-Path $root "scripts/run_kospi_dart_mda_poc_followup_chain_v1.py")
    } | Out-Null
}

Invoke-Step "logos_sync_studio_data" {
    Push-Location $no1k
    try {
        & npm run sync:logos-studio-data
    } finally {
        Pop-Location
    }
} | Out-Null

$gap = Invoke-Step "logos_deploy_gap_check" {
    & py (Join-Path $root "scripts/check_logos_studio_graph_slice_deploy_gap_v1.py")
}

$env:LOGOS_STUDIO_SMOKE_BASE = $SmokeBase.TrimEnd("/")
$smoke = Invoke-Step "logos_mindmap_playwright_smoke" {
    & node (Join-Path $no1k "scripts/smoke-logos-research-studio-mindmap-playwright-v1.mjs")
}

$wtp = Invoke-Step "oracle_wtp_readiness" {
    & py (Join-Path $root "scripts/run_oracle_logos_wtp_discovery_readiness_v1.py")
}

$gapDoc = @{}
$gapPath = Join-Path $root "reports/logos_studio_graph_slice_deploy_gap_v1_latest.json"
if (Test-Path -LiteralPath $gapPath) {
    $gapDoc = Get-Content -LiteralPath $gapPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$smokeDoc = @{}
$smokePath = Join-Path $root "reports/logos_studio_mindmap_playwright_smoke_v1_latest.json"
if (Test-Path -LiteralPath $smokePath) {
    $smokeDoc = Get-Content -LiteralPath $smokePath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$deployPending = [bool]$gapDoc.deploy_pending
$smokeOk = [bool]$smokeDoc.ok
# Solo: workspace ready + deploy gap explains prod smoke fail
$routineOk = ($gap.ok -and $wtp.ok) -and ($smokeOk -or $deployPending)

$nextActions = [System.Collections.Generic.List[string]]::new()
if ($deployPending -and -not $smokeOk) {
    $nextActions.Add("Deploy logos.jema-ai.com — public/data/logos_studio/graph_slice_v1.json (Jer.31.4 stub)") | Out-Null
}
if ($wtp.ok) {
    $nextActions.Add("WTP call 1 when lead exists — reports/logos_studio_b2b_wtp_discovery_call_1_v1.md") | Out-Null
}
if (-not $SkipKospiMaintenance) {
    $nextActions.Add("KOSPI maintenance: py scripts/run_kospi_dart_mda_poc_followup_chain_v1.py") | Out-Null
}

$doc = @{
    schema = "mkm_solo_logos_studio_demo_routine_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    research_only = $true
    send_gate = "HOLD"
    ok = $routineOk
    smoke_base = $env:LOGOS_STUDIO_SMOKE_BASE
    deploy_pending = $deployPending
    smoke_ok = $smokeOk
    steps = $steps
    commander_next_actions = @($nextActions)
    demo_url = "https://logos.jema-ai.com/logos-research/studio?q=job_job_suffering_reason&autorun=1&demo=1"
    reproduce = "powershell -File scripts/Invoke-MkmSoloLogosStudioDemoRoutine_v1.ps1"
} | ConvertTo-Json -Depth 6

Set-Content -LiteralPath $out -Value ($doc + "`n") -Encoding UTF8
Write-Host ($doc | ConvertFrom-Json | ConvertTo-Json -Compress)
if (-not $routineOk) { exit 1 }
exit 0
