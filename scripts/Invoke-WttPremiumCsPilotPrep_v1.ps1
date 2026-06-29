# Premium CS ICP prep: template 20 + validate + stress deck + solo auto routine.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipSoloAuto,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$template = Join-Path $WorkspaceRoot "data/wtt/templates/wtt_premium_cs_customer_masked_v1.template.jsonl"

Write-Host "=== WTT Premium CS pilot prep (ICP P0) ===" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DryRun] template -> validate -> stress deck -> solo auto" -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== 1/4: build Premium CS fill template (20) ===" -ForegroundColor Cyan
& py scripts/build_wtt_premium_cs_customer_template_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 2/4: validate template (schema + PII) ===" -ForegroundColor Cyan
& py scripts/validate_wtt_pilot_jsonl_v1.py --jsonl $template --min-sessions 20 --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== 3/4: Stress Certified deck ===" -ForegroundColor Cyan
$rq025Auto = Join-Path $WorkspaceRoot "reports/rq025_upstream_csv_auto_resolve_v1_latest.json"
$deckArgs = @()
if (Test-Path -LiteralPath $rq025Auto) {
    $deckArgs += "--include-rq025-appendix"
}
& py scripts/build_wtt_stress_certified_deck_v1.py @deckArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipSoloAuto) {
    Write-Host "=== 4/4: solo auto routine ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttPilotSoloAutoRoutine_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== 4/4: skipped solo auto ===" -ForegroundColor DarkGray
}

Write-Host "OK template: $template" -ForegroundColor Green
Write-Host "OK deck: reports/wtt_stress_certified_deck_v1_latest.md" -ForegroundColor Green
Write-Host "Next: fill [FILL] -> copy to data/wtt/intake/ -> Run-WttPilotIntake (no stub flags)" -ForegroundColor Yellow
exit 0
