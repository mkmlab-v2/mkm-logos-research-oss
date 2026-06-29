#Requires -Version 5.1
<#
.SYNOPSIS
  Economy auditable cinematic PoC — gate + local animatic (no Veo API unless env opt-in).

.DESCRIPTION
  **One-off / on-demand** auditable cinematic PoC — run manually when building the proof bundle.
  Not a weekly ops job (no scheduled task).
  Default: --hero-animatic-only (scenario-aligned, zero Vertex spend).
#>
param(
    [switch]$AllowVeoSpend,
    [switch]$VeoSmoke,
    [switch]$ReuseLocalHero
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Gate = Join-Path $Root "scripts\cinematic\check_cinematic_veo_spend_gate_v1.py"
$Poc = Join-Path $Root "scripts\cinematic\run_auditable_cinematic_poc_v1.py"
$Log = Join-Path $Root "reports\cinematic_poc_economy_log.jsonl"

if (-not (Test-Path -LiteralPath $Gate)) { throw "Missing: $Gate" }
if (-not (Test-Path -LiteralPath $Poc)) { throw "Missing: $Poc" }

Push-Location $Root
try {
    & py $Gate
    if ($LASTEXITCODE -ne 0) { throw "spend gate exit $LASTEXITCODE" }

    $pocArgs = @($Poc)
    if ($AllowVeoSpend) { $pocArgs += "--allow-veo-spend" }
    if ($VeoSmoke) { $pocArgs += "--veo-smoke" }
    if (-not $ReuseLocalHero) { $pocArgs += "--hero-animatic-only" }

    $out = & py @pocArgs 2>&1
    $code = $LASTEXITCODE
    $out | Write-Host
    if ($code -ne 0) { throw "poc exit $code" }

    $summary = $out | Select-Object -Last 1
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $line = (@{
        schema = "cinematic_poc_economy_run_v1"
        generated_at_utc = $ts
        exit_code = $code
        allow_veo_spend = [bool]$AllowVeoSpend
        hero_animatic_only = -not $ReuseLocalHero
        summary_json = $summary
    } | ConvertTo-Json -Compress)
  $line | Add-Content -LiteralPath $Log -Encoding utf8
    Write-Host "logged: $Log"
    exit 0
}
finally {
    Pop-Location
}
