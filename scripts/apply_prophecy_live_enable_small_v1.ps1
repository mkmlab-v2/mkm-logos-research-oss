#Requires -Version 5.1
<#
.SYNOPSIS
  소액 실매매 opt-in: live-enable 이벤트·롤백·체크리스트·GO/NO_GO·VPS 동기화.

.DESCRIPTION
  B-track ensemble v2 승인 이후, 별도 live-enable 승인(지휘관)을 디스크에 기록하고
  로컬 risk/GO 아티팩트를 갱신한 뒤 vps-mkmlife destiny 트리에 푸시한다.
  PM2 재시작은 -RestartPm2 시에만 (bitcoin-live-small-24h 단일 앱).

  주문 실행·API 호출은 PM2 런타임·VPS .env 범위. 본 스크립트는 아티팩트·동기화만.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\apply_prophecy_live_enable_small_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\apply_prophecy_live_enable_small_v1.ps1 -RestartPm2
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$Pm2App = "bitcoin-live-small-24h",
    [double]$MaxDailyLossPct = 2.0,
    [switch]$SkipVps,
    [switch]$RestartPm2
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

Write-Host "==> live-enable artifacts (small / conservative rollback)" -ForegroundColor Cyan
py scripts\build_prophecy_live_rollback_policy_v1.py --max-daily-loss-pct $MaxDailyLossPct
if ($LASTEXITCODE -ne 0) { throw "rollback policy: $LASTEXITCODE" }

py scripts\record_prophecy_live_enable_event_v1.py `
    --reviewer PRO `
    --decision APPROVED `
    --note "지휘관 in-chat 소액 실매매 승인 (2026-05-15): ensemble v2 pass + conservative caps." `
    --evidence-bundle docs/final/artifacts/prophecy_gate_evidence_pack_v1_latest.json `
    --rollback-trigger disable_live_on_gate_fail_or_loss_threshold_breach
if ($LASTEXITCODE -ne 0) { throw "live enable event: $LASTEXITCODE" }

py scripts\build_prophecy_live_enable_checklist_v1.py
if ($LASTEXITCODE -ne 0) { throw "live enable checklist: $LASTEXITCODE" }

$cl = Get-Content "docs\final\artifacts\prophecy_live_enable_checklist_v1_latest.json" -Raw | ConvertFrom-Json
if (-not $cl.summary.ready_to_enable_live) {
    throw "live_enable_checklist not ready: $($cl.summary.next_action)"
}

py scripts\build_prophecy_manual_live_switch_packet_v1.py
if ($LASTEXITCODE -ne 0) { throw "live switch packet: $LASTEXITCODE" }

$pkt = Get-Content "docs\final\artifacts\prophecy_manual_live_switch_packet_v1_latest.json" -Raw | ConvertFrom-Json
Write-Host "live_switch_packet status=$($pkt.status)" -ForegroundColor Yellow

Write-Host "==> local risk + GO/NO_GO chain" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Run-FactSafeRiskProfileSyncChain_v1.ps1 -ExitZeroOnNoGo
if ($LASTEXITCODE -ne 0) { throw "FactSafe chain: $LASTEXITCODE" }

py scripts\build_trading_go_nogo_status_v1.py
if ($LASTEXITCODE -ne 0) { throw "build_trading_go_nogo: $LASTEXITCODE" }

$go = Get-Content "docs\final\artifacts\trading_go_no_go_latest.json" -Raw | ConvertFrom-Json
Write-Host "local go_no_go=$($go.go_no_go) risk_mode=$($go.risk_mode)" -ForegroundColor $(if ($go.go_no_go -eq 'GO') { 'Green' } else { 'Yellow' })

powershell -NoProfile -ExecutionPolicy Bypass -File projects\bitcoin-trading\scripts\preflight_live_trading_readiness.ps1
if ($LASTEXITCODE -ne 0) { Write-Host "preflight exit $LASTEXITCODE (informational)" -ForegroundColor Yellow }

if ($SkipVps) {
    Write-Host "SkipVps: local artifacts only." -ForegroundColor Yellow
    exit 0
}

Write-Host "==> VPS GO/approval sync ($VpsHost)" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-VpsTradingGoReadinessSync_v1.ps1 `
    -WorkspaceRoot $WorkspaceRoot -VpsHost $VpsHost -DestinyRoot $DestinyRoot
if ($LASTEXITCODE -ne 0) { throw "VpsTradingGoReadinessSync: $LASTEXITCODE" }

$riskLocal = "projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
$remoteRisk = "$DestinyRoot/projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json"
Write-Host "==> SCP risk profile -> VPS" -ForegroundColor Cyan
ssh $VpsHost "mkdir -p '$DestinyRoot/projects/bitcoin-trading/memory/v2/risk'"
if ($LASTEXITCODE -ne 0) { throw "ssh mkdir: $LASTEXITCODE" }
scp $riskLocal "${VpsHost}:${remoteRisk}"
if ($LASTEXITCODE -ne 0) { throw "scp risk: $LASTEXITCODE" }

$remoteProbe = @"
cd '$DestinyRoot' && pm2 show $Pm2App 2>/dev/null | head -n 25; echo '---'; grep -E '^(ENABLE_TRADING|TESTNET)=' .env 2>/dev/null | sed 's/=.*$/=***/' || true; echo '---'; python3 -c \"import json; p='$DestinyRoot/docs/final/artifacts/trading_go_no_go_latest.json'; d=json.load(open(p)); print('vps_go_no_go', d.get('go_no_go'), 'risk', d.get('risk_mode'))\"
"@
Write-Host "==> VPS probe (pm2 + go_no_go, secrets redacted)" -ForegroundColor Cyan
ssh $VpsHost $remoteProbe
if ($LASTEXITCODE -ne 0) { Write-Host "VPS probe failed (SSH?); local artifacts are still updated." -ForegroundColor Yellow }

if ($RestartPm2) {
    if ($go.go_no_go -ne 'GO') {
        throw "Refusing PM2 restart: local go_no_go=$($go.go_no_go)"
    }
    Write-Host "==> pm2 restart $Pm2App (single app only)" -ForegroundColor Cyan
    ssh $VpsHost "cd '$DestinyRoot' && pm2 restart $Pm2App"
    if ($LASTEXITCODE -ne 0) { throw "pm2 restart: $LASTEXITCODE" }
}

Write-Host "DONE apply_prophecy_live_enable_small_v1 (RestartPm2=$RestartPm2)" -ForegroundColor Green
