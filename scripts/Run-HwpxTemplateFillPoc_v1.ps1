#Requires -Version 5.1
<#
.SYNOPSIS
  B-track HWPX template fill PoC: smoke (optional) -> build template -> fill from slots JSON.
.PARAMETER UserTemplate
  Official .hwpx path (overrides bundled PoC template).
.PARAMETER SlotsJson
  Slot mapping JSON (default: data/btrack/hwpx_poc/slots_v1.example.json).
.PARAMETER SmokeOnly
  Run check_hwpx_template_fill_smoke_v1.py only.
#>
param(
    [string]$UserTemplate = "",
    [string]$SlotsJson = "",
    [switch]$SmokeOnly,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $SkipSmoke) {
    Write-Host "== HWPX template fill smoke ==" -ForegroundColor Cyan
    py scripts/check_hwpx_template_fill_smoke_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($SmokeOnly) {
        Write-Host "[DONE] reports/hwpx_template_fill_smoke_latest.json" -ForegroundColor Green
        exit 0
    }
}

Write-Host "== Build PoC template ==" -ForegroundColor Cyan
py scripts/build_hwpx_poc_template_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$fillArgs = @("scripts/run_hwpx_template_fill_poc_v1.py")
if ($SlotsJson) { $fillArgs += @("--slots-json", $SlotsJson) }
if ($UserTemplate) { $fillArgs += @("--user-template", $UserTemplate) }

Write-Host "== Fill template ==" -ForegroundColor Cyan
py @fillArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] reports/hwpx_poc/hwpx_template_fill_poc_latest.json" -ForegroundColor Green
