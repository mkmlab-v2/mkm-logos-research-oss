#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only: trading GO/NO_GO legs, LOCKED vs ACTIVE policy, and operator next steps (no orders).

.DESCRIPTION
  Consolidates disk SSOT for "why NO_GO" and a tiered comfort model. Does not change prophecy mode
  or place trades. To refresh artifacts after sync, run Run-FactSafeRiskProfileSyncChain_v1.ps1 first.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-TradingComfortReadinessBrief_v1.ps1
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

$goPath = Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json"
$prophecyPath = Join-Path $WorkspaceRoot "docs\final\artifacts\prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
$riskPath = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\risk\risk_profile_fact_safe_latest.json"
$outJson = Join-Path $WorkspaceRoot "reports\trading_comfort_readiness_brief_latest.json"

function Read-JsonObj([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

$go = Read-JsonObj $goPath
$prophecy = Read-JsonObj $prophecyPath
$risk = Read-JsonObj $riskPath

$badge = $prophecy.meta.reliability_badge
$hrGate = $prophecy.meta.high_reliability_decision
$priceLocked = [bool]$prophecy.meta.price_output_locked
$riskMode = $risk.trinity_governor.mode
$govRegime = $risk.governance_bridge.final_regime
$govAllow = $risk.governance_bridge.final_action_allowed

$tiers = @(
    @{
        tier = 'A_observation'
        label = 'Observation comfort while LOCKED is OK'
        ok_when = 'live_sync fresh, tasks OK, preflight run; NO_GO only from LOCKED is policy-normal'
        commands = @(
            'scripts/Invoke-SafeOpsSurfaceCheck.ps1',
            'scripts/Verify-TradingAutomationHealth.ps1 -AllowPolicyLockedGoNoGo',
            'projects/bitcoin-trading/scripts/preflight_live_trading_readiness.ps1'
        )
    },
    @{
        tier = 'B_disk_go'
        label = 'Disk SSOT all GO before limited execution'
        ok_when = 'prophecy risk_profile.mode ACTIVE_MODE plus approval GO plus gate_ok plus risk_ok'
        commands = @(
            'scripts/Run-FactSafeRiskProfileSyncChain_v1.ps1',
            'scripts/build_trading_go_nogo_status_v1.py'
        )
        unlock_note = 'ACTIVE_MODE when prophecy hold_mode is false; LOW badge or HOLD keeps LOCKED by design'
    },
    @{
        tier = 'C_live_scale'
        label = 'Live scale after human sign-off'
        ok_when = 'tier B plus VPS aligned plus PM2 cwd verified plus caps and TTL rechecked'
        commands = @(
            'scripts/Invoke-VpsTradingGoReadinessSync_v1.ps1',
            'projects/bitcoin-trading/scripts/preflight_live_trading_readiness.ps1'
        )
    }
)

$payload = [ordered]@{
    schema = "trading_comfort_readiness_brief_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root = $WorkspaceRoot
    go_no_go = $go.go_no_go
    go_reasons = @($go.reasons)
    approval_ok = $go.approval_ok
    approval_decision = $go.approval_decision
    approval_valid_until_utc = $go.approval_valid_until_utc
    gate_ok = $go.gate_ok
    gate_reason = $go.gate_reason
    risk_ok = $go.risk_ok
    risk_mode = $go.risk_mode
    prophecy_reliability_badge = $badge
    prophecy_high_reliability_decision = $hrGate
    prophecy_price_output_locked = $priceLocked
    risk_trinity_mode = $riskMode
    governance_final_regime = $govRegime
    governance_final_action_allowed = $govAllow
    comfort_tiers = $tiers
    interpretation = @(
        'NO_GO with human GO is not a bug: Trinity LOCKED + low-reliability prophecy is conservative by design.',
        'Worry-free does not mean guaranteed profit; it means bounded loss, visible gates, and scheduled checks.',
        'Do not force ACTIVE_MODE without improving prophecy reliability / hold gate; use tier A until then.'
    )
}

$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outJson -Encoding UTF8

Write-Host "== Trading comfort readiness (read-only) ==" -ForegroundColor Cyan
Write-Host "go_no_go: $($go.go_no_go)  reasons: $($go.reasons -join ', ')"
Write-Host "approval: $($go.approval_decision) (ok=$($go.approval_ok)) until $($go.approval_valid_until_utc)"
Write-Host "gate: ok=$($go.gate_ok) reason=$($go.gate_reason)"
Write-Host "risk: ok=$($go.risk_ok) trinity=$($go.risk_mode) expires=$($go.risk_expires_at)"
Write-Host "prophecy: badge=$badge hr_gate=$hrGate price_locked=$priceLocked"
Write-Host "governance: regime=$govRegime final_action_allowed=$govAllow"
Write-Host ""
Write-Host "Tier A (observation OK while LOCKED): SafeOps + automation health (AllowPolicyLocked) + preflight"
Write-Host "Tier B (disk GO): prophecy ACTIVE_MODE + sync chain + go builder exit 0"
Write-Host "Tier C (live scale): B + VPS sync + PM2/human caps"
Write-Host "Wrote: $outJson" -ForegroundColor Green
exit 0
