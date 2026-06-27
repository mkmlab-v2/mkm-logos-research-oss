#Requires -Version 5.1
<#
.SYNOPSIS
  Fact-Safe 리스크 프로필 동기화 → 조건부 게이트 요약(dry-run) → trading GO/NO_GO 재빌드.

.DESCRIPTION
  주문·실매매 없음. 기본은 Git·예약 작업 SSOT용 `sync_fact_safe_risk_profile.py --repo-source --allow-metadata-downgrade`(기존 `n8n.*` 디스크 태그 이전 허용).
  레거시 n8n 메타데이터 태그가 필요하면 `-UseN8nSource`로 `--n8n-source` 전환.
  MKM_WORKSPACE_MAINTENANCE 활성 시 sync는 스킵(exit 0)될 수 있음.

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-FactSafeRiskProfileSyncChain_v1.ps1
.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Run-FactSafeRiskProfileSyncChain_v1.ps1 -UseN8nSource
.EXAMPLE
  예약 작업(스케줄러): `NO_GO`여도 동기화·게이트·아티팩트 갱신은 성공으로 남기려면 `-ExitZeroOnNoGo`.
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [switch]$UseN8nSource,
    # When set, `build_trading_go_nogo_status_v1.py --exit-zero-on-no-go` so exit 0 on legitimate NO_GO (scheduled hygiene).
    [switch]$ExitZeroOnNoGo
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

$syncLabel = if ($UseN8nSource) { "n8n-source (legacy)" } else { "repo-source (default)" }
Write-Host "==> 1/3 sync_fact_safe_risk_profile ($syncLabel)" -ForegroundColor Cyan
if ($UseN8nSource) {
    & $py $sync --n8n-source
} else {
    & $py $sync --repo-source --allow-metadata-downgrade
}
if ($LASTEXITCODE -ne 0) { throw "sync_fact_safe_risk_profile exit $LASTEXITCODE" }

Write-Host "==> 1b/3 check_logos_track_a_miswire_guard_v1" -ForegroundColor Cyan
$miswire = Join-Path $WorkspaceRoot "scripts\check_logos_track_a_miswire_guard_v1.py"
& $py $miswire
if ($LASTEXITCODE -ne 0) { throw "check_logos_track_a_miswire_guard_v1 exit $LASTEXITCODE" }

Write-Host "==> 2/3 conditional_action_gate (api dry-run, no backend)$(if ($ExitZeroOnNoGo) { ' (--dry-run-exit-zero-on-block)' })" -ForegroundColor Cyan
$gateArgs = @("--backend", "api", "--dry-run", "--skip-human-approval", "--skip-frame-payload")
if ($ExitZeroOnNoGo) { $gateArgs += "--dry-run-exit-zero-on-block" }
& $py $gate @gateArgs
if ($LASTEXITCODE -ne 0) { throw "run_conditional_action_gate_v1 exit $LASTEXITCODE" }

Write-Host "==> 3/3 build_trading_go_nogo_status$(if ($ExitZeroOnNoGo) { ' (--exit-zero-on-no-go)' })" -ForegroundColor Cyan
if ($ExitZeroOnNoGo) {
    & $py $status --exit-zero-on-no-go
} else {
    & $py $status
}
if ($LASTEXITCODE -ne 0) { throw "build_trading_go_nogo_status_v1 exit $LASTEXITCODE (NO_GO or error)" }

Write-Host "[ok] Fact-Safe risk sync chain complete." -ForegroundColor Green
exit 0
