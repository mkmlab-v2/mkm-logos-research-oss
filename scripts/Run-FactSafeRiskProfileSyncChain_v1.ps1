#Requires -Version 5.1
<#
.SYNOPSIS
  Fact-Safe 리스크 프로필 동기화 → 조건부 게이트 요약(dry-run) → trading GO/NO_GO 재빌드.

.DESCRIPTION
  주문·실매매 없음. n8n 메타데이터 유지(--n8n-source). MKM_WORKSPACE_MAINTENANCE 활성 시 sync는 스킵(exit 0)될 수 있음.

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-FactSafeRiskProfileSyncChain_v1.ps1
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $WorkspaceRoot

$py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path -LiteralPath $py)) {
    $py = (Get-Command -Name "py" -ErrorAction Stop).Source
}

$sync = Join-Path $WorkspaceRoot "scripts\sync_fact_safe_risk_profile.py"
$gate = Join-Path $WorkspaceRoot "projects\bitcoin-trading\scripts\run_conditional_action_gate_v1.py"
$status = Join-Path $WorkspaceRoot "scripts\build_trading_go_nogo_status_v1.py"

foreach ($p in @($sync, $gate, $status)) {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing: $p" }
}

Write-Host "==> 1/3 sync_fact_safe_risk_profile (--n8n-source)" -ForegroundColor Cyan
& $py $sync --n8n-source
if ($LASTEXITCODE -ne 0) { throw "sync_fact_safe_risk_profile exit $LASTEXITCODE" }

Write-Host "==> 2/3 conditional_action_gate (api dry-run, no backend)" -ForegroundColor Cyan
& $py $gate --backend api --dry-run --skip-human-approval --skip-frame-payload
if ($LASTEXITCODE -ne 0) { throw "run_conditional_action_gate_v1 exit $LASTEXITCODE" }

Write-Host "==> 3/3 build_trading_go_nogo_status" -ForegroundColor Cyan
& $py $status
if ($LASTEXITCODE -ne 0) { throw "build_trading_go_nogo_status_v1 exit $LASTEXITCODE (NO_GO or error)" }

Write-Host "[ok] Fact-Safe risk sync chain complete." -ForegroundColor Green
exit 0
