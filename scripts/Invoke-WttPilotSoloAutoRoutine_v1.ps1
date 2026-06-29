# Solo dev one-click: enrollment + spicy FSM + internal stub rehearsal + sales sheet render.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipStubIntake,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$reportOut = Join-Path $WorkspaceRoot "reports/wtt_pilot_solo_auto_routine_v1_latest.json"
$stubJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"
$spicyJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_spicy_masked_sessions_v1.example.jsonl"

Write-Host "=== WTT solo auto routine (1-person dev) ===" -ForegroundColor Cyan
Write-Host "legal: none — PUBLIC_FACING self-check only | SEND_GATE HOLD on synthetic/stub" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] enrollment -> spicy fsm -> solo drill -> stub intake -> sales render" -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== 1/5: enrollment routine ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPilotEnrollmentRoutine_v1.ps1 -SkipIntakeRehearsal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/5: solo internal drill report ===" -ForegroundColor Cyan
& py scripts/check_wtt_customer_masked_intake_drill_v1.py --solo-internal-rehearsal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipStubIntake) {
    Write-Host "=== 3/5: stub intake rehearsal (internal only) ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 `
        -TenantId wtt-solo-internal-v1 `
        -SessionJsonl $stubJsonl `
        -AllowStubTemplate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== 3/5: skipped stub intake ===" -ForegroundColor DarkGray
}

Write-Host "=== 4/5: spicy corpus FSM batch (stress SSOT last) ===" -ForegroundColor Cyan
& py scripts/run_wtt_spicy_corpus_fsm_batch_v1.py --jsonl $spicyJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 5/5: sales sheet render (solo self-check) ===" -ForegroundColor Cyan
& py scripts/build_governed_ai_customization_sales_sheet_render_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& py scripts/build_wtt_pilot_solo_auto_routine_report_v1.py --out $reportOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK report: $reportOut" -ForegroundColor Green
Write-Host "OK sales MD: reports/governed_ai_customization_sales_sheet_v1_latest.md" -ForegroundColor Green
exit 0
