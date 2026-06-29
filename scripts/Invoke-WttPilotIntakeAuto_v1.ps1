# Auto-resolve tenant_id + session JSONL -> validate -> intake -> n30 gate (no synthetic/stub flags).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "",
    [string]$SessionJsonl = "",
    [switch]$PreferNewest,
    [switch]$SkipN30Gate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$resolveOut = Join-Path $WorkspaceRoot "reports/wtt_pilot_intake_resolve_v1_latest.json"

Write-Host "=== WTT pilot intake AUTO (tenant + session resolve) ===" -ForegroundColor Cyan
Write-Host "SEND_GATE HOLD | no -AllowSynthetic / -AllowStubTemplate" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] resolve -> Run-WttPilotIntake -> check_wtt_human_n30_gate" -ForegroundColor DarkGray
    exit 0
}

$resolveArgs = @("scripts/resolve_wtt_pilot_intake_target_v1.py", "--out", $resolveOut)
if ($TenantId -ne "") { $resolveArgs += @("--tenant-id", $TenantId) }
if ($SessionJsonl -ne "") { $resolveArgs += @("--session-jsonl", $SessionJsonl) }
if ($PreferNewest) { $resolveArgs += "--prefer-newest" }

& py @resolveArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "Resolve failed. Drop file: data/wtt/intake/<tenant-slug>.jsonl (e.g. acme-wtt-pilot-v1.jsonl)" -ForegroundColor DarkYellow
    Write-Host "Or edit: docs/final/artifacts/wtt_pilot_active_tenant_v1_latest.json" -ForegroundColor DarkGray
    exit $LASTEXITCODE
}

$resolved = Get-Content -LiteralPath $resolveOut -Raw | ConvertFrom-Json
$tid = [string]$resolved.tenant_id
$sess = [string]$resolved.session_jsonl
Write-Host "Resolved: tenant=$tid session=$sess ($($resolved.resolution))" -ForegroundColor Green

& powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 `
    -TenantId $tid `
    -SessionJsonl $sess
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipN30Gate) {
    Write-Host "=== n30 gate sync ===" -ForegroundColor Cyan
    & py scripts/check_wtt_human_n30_gate_v1.py --sync-pack
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK auto intake complete (SEND HOLD until provenance + n30)" -ForegroundColor Green
exit 0
