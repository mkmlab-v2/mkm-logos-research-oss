#Requires -Version 5.1
<#
.SYNOPSIS
  Run bounded lane loop for ms · oracle · infra · design (shadow mechanical runner).

.DESCRIPTION
  NOT infinite Cursor chat. Does NOT enqueue todo_queue or promote Track A.
  SSOT per lane: reports/bounded_lane_loop_v1_latest.json (last lane wins summary)
  Audit: reports/bounded_lane_loop_audit.jsonl

.EXAMPLE
  powershell -File scripts\Invoke-BoundedLaneLoopAllLanes_v1.ps1 -DryRun

.EXAMPLE
  powershell -File scripts\Invoke-BoundedLaneLoopAllLanes_v1.ps1 -RefreshPin -MetaLayerEnvelopePath docs\final\artifacts\fixtures\mkm_meta_layer_turn_envelope_v1.example.json
#>
param(
    [ValidateSet("ms", "oracle", "infra", "design")]
    [string[]]$Lanes = @("ms", "oracle", "infra", "design"),
    [string]$MetaLayerEnvelopePath = "",
    [switch]$MetaLayerEnvelopeAppend,
    [switch]$RefreshPin,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "C:\workspace" }
Set-Location $Root

$invoke = Join-Path $PSScriptRoot "Invoke-BoundedLaneLoop_v1.ps1"
if (-not (Test-Path -LiteralPath $invoke)) {
    throw "Missing: $invoke"
}

$results = @()
$exit = 0

foreach ($lane in $Lanes) {
    Write-Host ""
    Write-Host "=== bounded lane loop: $lane ===" -ForegroundColor Cyan
    $args = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $invoke,
        "-Lane", $lane
    )
    if ($RefreshPin) { $args += "-RefreshPin" }
    if ($DryRun) { $args += "-DryRun" }
    if ($MetaLayerEnvelopePath) {
        $args += @("-MetaLayerEnvelopePath", $MetaLayerEnvelopePath)
    }
    if ($MetaLayerEnvelopeAppend) { $args += "-MetaLayerEnvelopeAppend" }

    & powershell @args
    $rc = $LASTEXITCODE
    $outcome = "unknown"
    $summaryPath = Join-Path $Root "reports\bounded_lane_loop_v1_latest.json"
    if (Test-Path -LiteralPath $summaryPath) {
        try {
            $doc = Get-Content -LiteralPath $summaryPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($doc.lane -eq $lane) { $outcome = [string]$doc.outcome_class }
        }
        catch { }
    }
    $results += [ordered]@{
        lane           = $lane
        exit_code      = $rc
        outcome_class  = $outcome
    }
    if ($rc -ne 0) { $exit = $rc }
}

Write-Host ""
Write-Host "=== bounded lane loop all-lanes summary ===" -ForegroundColor Green
$results | ForEach-Object {
    Write-Host ("  {0}: exit={1} outcome={2}" -f $_.lane, $_.exit_code, $_.outcome_class)
}

exit $exit
