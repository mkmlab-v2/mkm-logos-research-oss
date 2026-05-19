#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327: pre-export gates -> PDF export -> workflow status refresh.
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== OpenData 327 pre-export gates ==" -ForegroundColor Cyan
py scripts/check_opendata_327_pre_export_gates_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== OpenData 327 PDF export (Part B + C) ==" -ForegroundColor Cyan
py scripts/export_opendata_327_submission_pdf_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[DONE] OpenData 327 chain OK (gates workflow refreshed via Python UTF-8)" -ForegroundColor Green
