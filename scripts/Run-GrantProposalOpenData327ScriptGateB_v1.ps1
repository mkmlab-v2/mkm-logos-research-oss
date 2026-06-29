#Requires -Version 5.1
<#
.SYNOPSIS
  OpenData 327 §B Script Gate — 10 steps (LLM forbidden · green all before Lane A).
  SSOT: docs/final/artifacts/opendata_327_script_gate_runbook_v1_latest.md
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-GateStep {
    param(
        [string]$Name,
        [string]$Command
    )
    Write-Host "[GATE] $Name" -ForegroundColor Cyan
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Invoke-GateStep "1/10 G1 pre-export" "py scripts/check_opendata_327_pre_export_gates_v1.py"
Invoke-GateStep "2/10 G2 shipped-claim" "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode shipped"
Invoke-GateStep "3/10 OD1 overview forbidden" "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode overview"
Invoke-GateStep "4/10 OD4 shipped duplicate" "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode shipped"
Invoke-GateStep "5/10 technical_ready" "py scripts/build_opendata_327_submission_readiness_v1.py"
Invoke-GateStep "6/10 hold_gate_ready_fixture" "py scripts/check_opendata_327_draft_hold_v1.py --input-json tests/fixtures/opendata_327_policy_slot_ready_v1.json"
Invoke-GateStep "7/10 submission forbidden" "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode submission"
Invoke-GateStep "8/10 annex gate" "py scripts/check_opendata_327_pre_export_gates_v1.py"
Write-Host "[GATE] 9/10 BRN SSOT" -ForegroundColor Cyan
$brnPath = Join-Path $root "docs\final\artifacts\business_registration_plan_v1.md"
$overviewPath = Join-Path $root "docs\final\artifacts\ai_opendata_challenge_2026_327_business_plan_overview_v1.md"
if (Test-Path -LiteralPath $brnPath) {
    py -c "from pathlib import Path; import sys; sys.exit(0 if Path(r'$brnPath').is_file() else 1)"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} elseif (Test-Path -LiteralPath $overviewPath) {
    $ov = Get-Content -LiteralPath $overviewPath -Raw -Encoding UTF8
    if ($ov -notmatch '628-86-01742') {
        Write-Host "[FAIL] 9/10 BRN SSOT — overview meta missing BRN" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] 9/10 BRN via overview meta (artifact gitignored)" -ForegroundColor Yellow
} else {
    Write-Host "[FAIL] 9/10 BRN SSOT — no SSOT file" -ForegroundColor Red
    exit 1
}
Invoke-GateStep "10/10 tech disclosure" "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode tech"

Write-Host "[DONE] OpenData 327 Script Gate B — 10/10 exit 0" -ForegroundColor Green
