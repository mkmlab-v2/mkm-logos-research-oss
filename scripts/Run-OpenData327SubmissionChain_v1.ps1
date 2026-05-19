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

Write-Host "== Refresh pre-export workflow status ==" -ForegroundColor Cyan
$gatesPath = Join-Path $root "reports\opendata_327_pre_export_gates_latest.json"
$exportPath = Join-Path $root "reports\opendata_327_pdf_export_latest.json"
$gates = Get-Content -LiteralPath $gatesPath -Raw | ConvertFrom-Json
$export = Get-Content -LiteralPath $exportPath -Raw | ConvertFrom-Json
$partB = $export.parts | Where-Object { $_.pdf -like "*part_b*" } | Select-Object -First 1
$sizeMb = [math]::Round((Get-Item (Join-Path $root $partB.pdf)).Length / 1MB, 2)
$workflow = @{
  schema = "opendata_327_pre_export_gates_v1"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  all_gates_ok_for_export_draft = $gates.all_gates_ok_for_export_draft
  gates = $gates.gates
  workflow_step_status = @{
    step_1_strip_md = "completed"
    step_2_fill_placeholders = "completed_draft_targets"
    step_3_export_pdf = "completed"
    step_4_merge = "b_only_interim_no_cover_a"
    step_5_size_check = if ($sizeMb -lt 30) { "ok_under_30mb" } else { "over_30mb_review" }
    step_6_kstartup_dry_run = "scheduled_2026-06-01"
    step_7_final_submit = "scheduled_2026-06-04_05"
  }
  export_artifacts = @{
    part_b_pdf = $partB.pdf
    part_b_pdf_merge_name = $export.part_b_pdf_merge_name
    part_c_pdf = ($export.parts | Where-Object { $_.pdf -like "*part_c*" }).pdf
    part_b_html = $partB.html
    part_c_html = ($export.parts | Where-Object { $_.html -like "*part_c*" }).html
    part_b_size_mb = $sizeMb
  }
  merge_guide = "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.md"
  next_human = @(
    "K-Startup 표지(A) 양식 수동 병합 + Annex(D) 선택"
    "§2-2 목표안 수치는 제출 전 내부 벤치로 확정"
    "K-Startup + 나라장터 접수 (6/5 18:00)"
  )
}
$workflow | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $gatesPath -Encoding utf8

Write-Host "[DONE] OpenData 327 chain OK (Part B ~${sizeMb} MB)" -ForegroundColor Green
