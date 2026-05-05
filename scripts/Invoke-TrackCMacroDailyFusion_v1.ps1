<#
.SYNOPSIS
  Single daily entrypoint: Fragility+macro smoke (with weekly + webhooks) → forward log chain → Logos 4D X/Y → Track C ops dashboard.

.DESCRIPTION
  Avoids duplicate fragility runs: Invoke-FragilityMacroRiskDaily runs the full chain once; forward and logos chains use -SkipFragilityChain.

  Typical local test (no webhooks, no public exodus fetch):
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-TrackCMacroDailyFusion_v1.ps1 -SkipGateAlert -SkipExodusSourceFetch

  Optional meta-layer audit (after fusion steps): pass a JSON file or a markdown file containing a ```json envelope block.
    -File ... -MetaLayerEnvelopePath C:\path\envelope.json

.NOTES
  Scheduled task: Register-TrackCMacroDailyFusionTask.ps1 (use -UnregisterLegacyTasks when replacing
  MKM-Fragility-MacroRisk-Daily + MacroRiskForwardDailyChain). Re-register with the same -TaskName to
  change flags (e.g. -SkipExodusSourceFetch). Spot-check: Verify-TrackCMacroDailyFusionScheduledTask_v1.ps1.
#>
[CmdletBinding()]
param(
    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h",

    [switch]$SkipGateAlert,
    [switch]$SkipFailureAlert,

    [switch]$SkipExodusSourceFetch,
    [switch]$SkipForwardChain,
    [switch]$SkipLogosChain,
    [switch]$SkipOpsDashboard,

    # Optional: run mkm_meta_layer_envelope_v1.py after fusion (JSON path or markdown with ```json envelope).
    [string]$MetaLayerEnvelopePath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-FusionStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host "[trackc-macro-fusion] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Fusion step failed: $Name (exit=$LASTEXITCODE)"
    }
}

$fragilityDaily = Join-Path $PSScriptRoot "Invoke-FragilityMacroRiskDaily.ps1"
$forwardDaily = Join-Path $PSScriptRoot "run_macro_risk_forward_daily_chain_v1.ps1"
$logosChain = Join-Path $PSScriptRoot "run_logos_4d_state_chain_v1.ps1"
$opsDashboard = Join-Path $PSScriptRoot "build_mkm_trackc_ops_dashboard_v1.py"

$required = @($fragilityDaily, $forwardDaily, $logosChain)
if (-not $SkipOpsDashboard) {
    $required += $opsDashboard
}
foreach ($p in $required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Required file not found: $p"
    }
}

# 1) Fragility + macro risk API smoke + weekly fragility report + optional gate/failure webhooks
$fragArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $fragilityDaily,
    "-AssetScope", $AssetScope,
    "-Horizon", $Horizon
)
if ($PreferFred) { $fragArgs += "-PreferFred" }
if ($SkipGateAlert) { $fragArgs += "-SkipGateAlert" }
if ($SkipFailureAlert) { $fragArgs += "-SkipFailureAlert" }

Invoke-FusionStep -Name "Invoke-FragilityMacroRiskDaily (full chain)" -Action {
    powershell @fragArgs
}

# 2) Forward-testing chain (reuse fragility artifacts)
if (-not $SkipForwardChain) {
    $fwdArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $forwardDaily,
        "-SkipFragilityChain",
        "-AssetScope", $AssetScope,
        "-Horizon", $Horizon
    )
    if ($PreferFred) { $fwdArgs += "-PreferFred" }
    Invoke-FusionStep -Name "run_macro_risk_forward_daily_chain_v1" -Action {
        powershell @fwdArgs
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip forward daily chain (SkipForwardChain)"
}

# 3) Exodus source + pressure + logos 4D state (reuse fragility artifacts)
if (-not $SkipLogosChain) {
    $logosArgs = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", $logosChain,
        "-SkipFragilityChain",
        "-AssetScope", $AssetScope,
        "-Horizon", $Horizon
    )
    if ($PreferFred) { $logosArgs += "-PreferFred" }
    if ($SkipExodusSourceFetch) { $logosArgs += "-SkipExodusSourceFetch" }
    Invoke-FusionStep -Name "run_logos_4d_state_chain_v1" -Action {
        powershell @logosArgs
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip logos 4d chain (SkipLogosChain)"
}

# 4) Ops dashboard JSON (local artifacts)
if (-not $SkipOpsDashboard) {
    Invoke-FusionStep -Name "build_mkm_trackc_ops_dashboard_v1.py" -Action {
        Set-Location -LiteralPath $repoRoot
        py $opsDashboard
    }
}
else {
    Write-Host "[trackc-macro-fusion] skip ops dashboard (SkipOpsDashboard)"
}

if ([string]::IsNullOrWhiteSpace($MetaLayerEnvelopePath)) {
    Write-Host "[trackc-macro-fusion] skip meta-layer envelope (MetaLayerEnvelopePath empty)"
}
else {
    $metaPath = $MetaLayerEnvelopePath.Trim()
    if (-not (Test-Path -LiteralPath $metaPath)) {
        throw "MetaLayerEnvelopePath not found: $metaPath"
    }
    $pyGate = Join-Path $PSScriptRoot "mkm_meta_layer_envelope_v1.py"
    if (-not (Test-Path -LiteralPath $pyGate)) {
        throw "Required file not found: $pyGate"
    }
    Write-Host "[trackc-macro-fusion] meta-layer envelope gate: $metaPath"
    $mission = "trackc-macro-daily-fusion"
    $actor = "Invoke-TrackCMacroDailyFusion_v1"
    if ($metaPath.EndsWith(".json", [System.StringComparison]::OrdinalIgnoreCase)) {
        py $pyGate append --json-file $metaPath --repo-root $repoRoot --mission-id $mission --actor $actor
    }
    else {
        py $pyGate audit-markdown --markdown-file $metaPath --repo-root $repoRoot --mission-id $mission --actor $actor
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Meta-layer envelope gate failed (exit=$LASTEXITCODE)"
    }
}

Write-Host "[trackc-macro-fusion] PASS"
Write-Host "[trackc-macro-fusion] fragility_daily_json=$repoRoot/reports/fragility_macro_risk_daily_latest.json"
Write-Host "[trackc-macro-fusion] logos4d=$repoRoot/docs/final/artifacts/logos_4d_state_v1_latest.json"
Write-Host "[trackc-macro-fusion] ops_dashboard=$repoRoot/docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
