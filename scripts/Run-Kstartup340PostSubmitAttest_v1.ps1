# 창업패키지 340호 — 제출완료(G6) attest 원클릭 (human 제출 후에만 실행)
param(
    [string]$Note = "K-Startup 제출완료 확인",
    [string]$PmsTaskId = "20461210",
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

if ($WhatIfOnly) {
    Write-Host "py scripts/attest_kstartup_startup_package_ai_human_gates_v1.py --gate G6_submitted_complete --status pass --pms-task-id $PmsTaskId"
    Write-Host "py scripts/check_kstartup_startup_package_ai_forbidden_phrases_v1.py"
    Write-Host "py scripts/check_kstartup_startup_package_ai_submission_gate_v1.py"
    Write-Host "py scripts/build_kstartup_startup_package_ai_submission_archive_pack_v1.py"
    exit 0
}

Write-Host ">> G6 attest (Python note template)"
& py scripts/attest_kstartup_startup_package_ai_human_gates_v1.py --gate G6_submitted_complete --status pass --pms-task-id $PmsTaskId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">> forbidden scan"
& py scripts/check_kstartup_startup_package_ai_forbidden_phrases_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">> submission gate"
& py scripts/check_kstartup_startup_package_ai_submission_gate_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">> submission archive pack"
& py scripts/build_kstartup_startup_package_ai_submission_archive_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "G6_submitted_complete attested. Drop PMS receipt screenshot in reports/grant_submission_receipts/startup_package_ai_340_20461210/ then re-run archive pack."
