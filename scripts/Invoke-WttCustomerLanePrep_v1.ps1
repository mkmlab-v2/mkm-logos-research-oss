# Customer lane prep: Premium CS template + readiness + drop watch register + deck (SEND HOLD).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$RegisterDropWatch,
    [switch]$SkipPremiumTemplate,
    [switch]$SkipDeckRefresh,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "=== WTT Customer Lane Prep ===" -ForegroundColor Cyan
Write-Host "real customer path | operator_panel separate | SEND HOLD" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] premium template -> readiness -> register drop watch -> deck refresh" -ForegroundColor DarkGray
    exit 0
}

if (-not $SkipPremiumTemplate) {
    Write-Host "=== 1/4: Premium CS template (20 fill slots) ===" -ForegroundColor Cyan
    & py scripts/build_wtt_premium_cs_customer_template_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $template = Join-Path $WorkspaceRoot "data/wtt/templates/wtt_premium_cs_customer_masked_v1.template.jsonl"
    & py scripts/validate_wtt_pilot_jsonl_v1.py --jsonl $template --min-sessions 20 --strict
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== 1/4: skipped premium template ===" -ForegroundColor DarkGray
}

Write-Host "=== 2/4: customer intake readiness report ===" -ForegroundColor Cyan
& py scripts/check_wtt_customer_intake_readiness_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($RegisterDropWatch) {
    Write-Host "=== 3/4: register drop watch task (5 min poll) ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-WttPilotIntakeDropWatchTask.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify-WttPilotIntakeDropWatchScheduledTask_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== 3/4: drop watch register skipped (pass -RegisterDropWatch to enable) ===" -ForegroundColor DarkYellow
}

if (-not $SkipDeckRefresh) {
    Write-Host "=== 4/4: stress deck + operator panel SSOT refresh ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-WttOperatorPanelDeckRefresh_v1.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== 4/4: deck refresh skipped ===" -ForegroundColor DarkGray
}

Write-Host "OK readiness: reports/wtt_customer_intake_readiness_v1_latest.json" -ForegroundColor Green
Write-Host "Next: fill template -> copy to data/wtt/intake/<tenant>.jsonl -> human gate -> drop or auto intake" -ForegroundColor Yellow
exit 0
