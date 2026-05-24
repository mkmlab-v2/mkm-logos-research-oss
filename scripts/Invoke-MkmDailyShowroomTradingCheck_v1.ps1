#Requires -Version 5.1
<#
.SYNOPSIS
  Daily ~3min: comfort brief, Fact-Safe sync, observation brief, automation health, heartbeat, showroom HEAD.

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MkmDailyShowroomTradingCheck_v1.ps1
#>
[CmdletBinding()]
param([string]$WorkspaceRoot = "")

$ErrorActionPreference = "Stop"
$root = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else { $WorkspaceRoot }
Set-Location -LiteralPath $root

Write-Host "=== MKM daily showroom + trading check ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-TradingComfortReadinessBrief_v1.ps1")
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Run-FactSafeRiskProfileSyncChain_v1.ps1") -ExitZeroOnNoGo
& py (Join-Path $root "scripts\build_trading_observation_brief_v1.py")
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-LiveSyncHeartbeatCheck.ps1")
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Verify-TradingAutomationHealth.ps1") -AllowPolicyLockedGoNoGo
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Invoke-SafeOpsSurfaceCheck.ps1")
foreach ($u in @(
        "https://api.jemaai.cloud/public_showroom_board_minimal.html",
        "https://api.jemaai.cloud/public_showroom_trust_visualization_v0.html",
        "https://api.jemaai.cloud/showroom_trust_visualization_slice_v0.json"
    )) {
    try {
        $r = Invoke-WebRequest -Uri $u -Method Head -TimeoutSec 15 -UseBasicParsing
        Write-Host "[showroom] $u => $($r.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "[showroom] $u => FAIL $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
& py (Join-Path $root "scripts\check_showroom_trust_viz_public_chain_v1.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[showroom] trust viz public chain smoke FAILED (see reports/showroom_trust_viz_public_chain_smoke_latest.json)" -ForegroundColor Red
}
Write-Host "See: trading_observation_brief_latest.json, mkm_trackc_ops_dashboard_latest.json" -ForegroundColor DarkGray
exit 0
