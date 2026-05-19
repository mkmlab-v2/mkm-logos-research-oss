<#
.SYNOPSIS
  Cost-optimized weekly marketing bundle: unified queue sync -> LinkedIn assemble-only -> summary.

.DESCRIPTION
  Default tier_0 ($0 API): no -Gemini unless MKM_MARKETING_GEMINI_ALLOWED=1 and queue items allow_gemini.
  SSOT: docs/final/artifacts/marketing_ops_cost_tier_v1_latest.json

.PARAMETER Gemini
  Force Gemini for LinkedIn generation (overrides tier_0; use sparingly).

.PARAMETER WithChart
  Pass through to LinkedIn chain.

.PARAMETER WhatIfOnly
  Dry-run LinkedIn generator only (after sync).

.PARAMETER SkipLinkedIn
  Only sync queue + write summary (debug).
#>
param(
    [string]$WorkspaceRoot = "",
    [switch]$Gemini,
    [switch]$WithChart,
    [switch]$WhatIfOnly,
    [switch]$SkipLinkedIn
)

$ErrorActionPreference = "Stop"
$root = if ($WorkspaceRoot) { (Resolve-Path -LiteralPath $WorkspaceRoot).Path } else { Split-Path -Parent $PSScriptRoot }

$dotenv = Join-Path $root "scripts\Import-WorkspaceDotEnv_v1.ps1"
if (Test-Path -LiteralPath $dotenv) {
    . $dotenv -WorkspaceRoot $root
}

$sync = Join-Path $root "scripts\sync_marketing_queue_to_linkedin_v1.py"
$linkedin = Join-Path $root "scripts\run_linkedin_b2b_weekly_draft_chain_v1.ps1"
$summary = Join-Path $root "scripts\build_marketing_weekly_bundle_summary_v1.py"
$queuePath = Join-Path $root "data\marketing\marketing_content_queue.json"

Write-Host "== Marketing queue -> LinkedIn sync ==" -ForegroundColor Cyan
& py $sync --init-from-example
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$syncJson = & py $sync 2>&1 | Out-String
Write-Host $syncJson

if (Test-Path -LiteralPath $queuePath) {
    try {
        $q = Get-Content -LiteralPath $queuePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $tier = if ($q.active_cost_tier) { $q.active_cost_tier } else { $q.default_cost_tier }
        Write-Host ("active_cost_tier={0}" -f $tier) -ForegroundColor DarkCyan
        if ($q.tier15_event_week -and $q.tier15_event_week.enabled) {
            Write-Host "tier15_event_week=enabled (max 1-2 Gemini posts/month if MKM_MARKETING_GEMINI_ALLOWED=1)" -ForegroundColor Yellow
        }
    } catch {
        Write-Warning "Could not parse marketing_content_queue.json for tier hint."
    }
}

$useGemini = $false
if ($Gemini) {
    $allowed = $env:MKM_MARKETING_GEMINI_ALLOWED
    if ($allowed -match '^(1|true|yes|on)$') {
        $useGemini = $true
    } else {
        Write-Warning "MKM_MARKETING_GEMINI_ALLOWED not set; ignoring -Gemini (tier_0 default)."
    }
} elseif ($syncJson -match '"suggest_gemini_flag"\s*:\s*true') {
    if ($env:MKM_MARKETING_GEMINI_ALLOWED -match '^(1|true|yes|on)$') {
        $useGemini = $true
        Write-Host "Using -Gemini for allow_gemini queue items (MKM_MARKETING_GEMINI_ALLOWED=1)." -ForegroundColor Yellow
    }
}

$channels = Join-Path $root "scripts\generate_marketing_channel_draft_v1.py"

Write-Host "== YouTube / newsletter drafts (assemble-only) ==" -ForegroundColor Cyan
& py $channels --channel all
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipLinkedIn) {
    Write-Host "== LinkedIn B2B draft chain ==" -ForegroundColor Cyan
    $liParams = @{ WorkspaceRoot = $root }
    if ($useGemini) { $liParams["Gemini"] = $true }
    if ($WithChart) { $liParams["WithChart"] = $true }
    if ($WhatIfOnly) { $liParams["WhatIfOnly"] = $true }
    & $linkedin @liParams
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "== Bundle summary ==" -ForegroundColor Cyan
$sumArgs = @($summary)
if ($useGemini) { $sumArgs += "--gemini-used" }
& py @sumArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] tier SSOT: docs/final/artifacts/marketing_ops_cost_tier_v1_latest.json" -ForegroundColor Green
Write-Host "[DONE] summary: reports/marketing/marketing_weekly_bundle_latest.json" -ForegroundColor Green

Write-Host "== Phase 2 publish handoff ==" -ForegroundColor Cyan
$phase2 = Join-Path $root "scripts\Invoke-MarketingPublishPhase2_v1.ps1"
& $phase2 -WorkspaceRoot $root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

exit 0
