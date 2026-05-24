#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327: gates -> PDF export -> submission readiness JSON (one screen for commander).
.PARAMETER IncludeHwpxFill
  Optional B-track HWPX template fill smoke (research_only; does not replace PDF submission).
#>
param(
    [switch]$IncludeHwpxFill
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== OpenData 327 pre-export gates ==" -ForegroundColor Cyan
py scripts/check_opendata_327_pre_export_gates_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== OpenData 327 PDF export ==" -ForegroundColor Cyan
py scripts/export_opendata_327_submission_pdf_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Merge B+C+D (cover A manual) ==" -ForegroundColor Cyan
py scripts/merge_opendata_327_submission_pdf_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Submission readiness summary ==" -ForegroundColor Cyan
py scripts/build_opendata_327_submission_readiness_v1.py --refresh-parallel-checklist
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Commander handoff (fused) ==" -ForegroundColor Cyan
py scripts/build_opendata_327_commander_handoff_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeHwpxFill) {
    Write-Host "== HWPX template fill smoke (B-track, optional) ==" -ForegroundColor Cyan
    py scripts/check_hwpx_template_fill_smoke_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[DONE] reports/opendata_327_submission_readiness_latest.json + opendata_327_commander_handoff_latest.json" -ForegroundColor Green
