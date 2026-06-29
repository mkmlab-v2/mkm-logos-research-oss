# WTT pilot enrollment one-click: pack + readiness + customer stub + intake rehearsal + n30 gate.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipIntakeRehearsal,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$stubJsonl = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"

Write-Host "=== WTT pilot enrollment routine (auto) ===" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DryRun] pack -> readiness -> stub -> validate -> intake -> n30 gate" -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== 1/6: build pilot pack + enrollment slots ===" -ForegroundColor Cyan
& py scripts/build_warmth_trigger_pilot_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/6: enrollment readiness gate ===" -ForegroundColor Cyan
& py scripts/check_warmth_trigger_pilot_readiness_v1.py --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 3/6: build customer-masked stub template (20) ===" -ForegroundColor Cyan
& py scripts/build_wtt_customer_masked_stub_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 4/6: validate stub JSONL + PII ===" -ForegroundColor Cyan
& py scripts/validate_wtt_pilot_jsonl_v1.py --jsonl $stubJsonl --min-sessions 20 --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipIntakeRehearsal) {
    Write-Host "=== 5/6: WTT intake rehearsal (stub template) ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 `
        -TenantId wtt-customer-stub-v1 `
        -SessionJsonl $stubJsonl `
        -AllowStubTemplate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== 5/6: skipped intake rehearsal ===" -ForegroundColor DarkGray
}

Write-Host "=== 6/6: human n30 gate + checklist ===" -ForegroundColor Cyan
& py scripts/check_wtt_human_n30_gate_v1.py --sync-pack
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK checklist: docs/final/artifacts/wtt_pilot_enrollment_checklist_v1_latest.json" -ForegroundColor Green
Write-Host "OK gate report: reports/wtt_human_n30_gate_v1_latest.json" -ForegroundColor Green
exit 0
