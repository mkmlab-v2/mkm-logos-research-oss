#Requires -Version 5.1
<#
.SYNOPSIS
  Fact-Safe 리스크 프로필 주기 갱신 예약 작업 등록(기본 4시간마다).

.PARAMETER IntervalHours
  최소 2. `expires_at` 12h 전에 여유 있게 돌도록 **4 기본**.

.EXAMPLE
  pwsh -File scripts/Register-FactSafeRiskProfileSyncTask.ps1 -RunNow
  pwsh -File scripts/Register-FactSafeRiskProfileSyncTask.ps1 -Remove
.EXAMPLE
  pwsh -File scripts/Register-FactSafeRiskProfileSyncTask.ps1 -Force -UseN8nSourceInTask
#>
param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$TaskName = "\MKM-FactSafe-RiskProfile-Sync-4H",
    [ValidateRange(2, 23)]
    [int]$IntervalHours = 4,
    [switch]$Force,
    [switch]$RunNow,
    [switch]$Remove,
    [switch]$UseN8nSourceInTask
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$runner = Join-Path $WorkspaceRoot "scripts\Run-FactSafeRiskProfileSyncChain_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

if ($Remove) {
    cmd /c "schtasks /Delete /TN `"$TaskName`" /F >nul 2>nul" | Out-Null
    Write-Host "REMOVED (if existed): $TaskName"
    exit 0
}

if ($Force) {
    cmd /c "schtasks /Delete /TN `"$TaskName`" /F >nul 2>nul" | Out-Null
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$n8nArg = if ($UseN8nSourceInTask) { " -UseN8nSource" } else { "" }
$action = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$runner`"$n8nArg"
$user = "$env:USERDOMAIN\$env:USERNAME"

schtasks /Create /TN $TaskName /SC HOURLY /MO $IntervalHours /ST $startTime /TR $action /RU $user /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "schtasks register failed exit=$LASTEXITCODE task=$TaskName"
}

Write-Host "REGISTERED: $TaskName"
Write-Host "SCHEDULE: every ${IntervalHours}h from $startTime"
Write-Host "RUN_MANUAL: schtasks /Run /TN `"$TaskName`""

if ($RunNow) {
    Write-Host "==> Run now..." -ForegroundColor Cyan
    schtasks /Run /TN $TaskName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "schtasks /Run failed exit=$LASTEXITCODE"
    }
}
