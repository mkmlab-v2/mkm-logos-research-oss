[CmdletBinding()]
param(
    [switch]$IncludeApproval
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$quick = Join-Path $PSScriptRoot "Run-MacroRiskN8nOpsQuick.ps1"
$daily = Join-Path $PSScriptRoot "Run-MacroRiskN8nDailyCheck.ps1"
if (-not (Test-Path -LiteralPath $quick)) { throw "Missing $quick" }
if (-not (Test-Path -LiteralPath $daily)) { throw "Missing $daily" }

Write-Output "=== macro_risk_n8n_weekly_rehearse: health ==="
& $quick -Action health

Write-Output "=== macro_risk_n8n_weekly_rehearse: taillog ==="
& $quick -Action taillog

if ($IncludeApproval) {
    Write-Output "=== macro_risk_n8n_weekly_rehearse: approve (webhook -> n8n mail path) ==="
    & $quick -Action approve
}

Write-Output "=== macro_risk_n8n_weekly_rehearse: daily_check ==="
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $daily

Write-Output "macro_risk_n8n_weekly_rehearse: DONE"
