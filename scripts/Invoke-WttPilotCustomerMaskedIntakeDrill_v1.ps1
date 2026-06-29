# Customer-masked intake drill: checklist + optional real JSONL intake (no synthetic/stub).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "wtt-customer-live-v1",
    [string]$SessionJsonl = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$drillOut = Join-Path $WorkspaceRoot "reports/wtt_customer_masked_intake_drill_v1_latest.json"

Write-Host "=== WTT customer-masked intake drill ===" -ForegroundColor Cyan
Write-Host "SEND_GATE HOLD | no -AllowSynthetic / -AllowStubTemplate" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] drill report -> optional Run-WttPilotIntake_v1.ps1" -ForegroundColor DarkGray
    exit 0
}

$drillArgs = @("scripts/check_wtt_customer_masked_intake_drill_v1.py", "--out", $drillOut)
if ($SessionJsonl -ne "") {
    $drillArgs += @("--session-jsonl", $SessionJsonl)
}
& py @drillArgs
$drillExit = $LASTEXITCODE

if ($SessionJsonl -eq "" -or $drillExit -eq 2) {
    Write-Host "Drill: awaiting customer masked JSONL (exit $drillExit expected when missing)." -ForegroundColor DarkYellow
    Write-Host "Place 20-50 sessions then re-run with -SessionJsonl <path>" -ForegroundColor DarkGray
    exit 0
}

if ($drillExit -ne 0) { exit $drillExit }

Write-Host "=== Live customer-masked intake ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 `
    -TenantId $TenantId `
    -SessionJsonl $SessionJsonl
exit $LASTEXITCODE
