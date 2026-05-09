param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "\MKM-Trading-Guardian-Daily-Drill",
  [string]$RunAt = "06:10",
  [switch]$Force,
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$runner = Join-Path $WorkspaceRoot "scripts\Run-TradingGuardianDailyDrillTask.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner script not found: $runner"
}

if ($Force) {
  cmd /c "schtasks /Delete /TN `"$TaskName`" /F >nul 2>nul" | Out-Null
}

$action = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$user = "$env:USERDOMAIN\$env:USERNAME"

schtasks /Create /TN $TaskName /SC DAILY /ST $RunAt /TR $action /RU $user /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to register task via schtasks (exit=$LASTEXITCODE): $TaskName"
}

Write-Host "REGISTERED: $TaskName"
Write-Host "SCHEDULE: DAILY AT $RunAt"
Write-Host "RUN_MANUAL: schtasks /Run /TN `"$TaskName`""
Write-Host "QUERY: schtasks /Query /TN `"$TaskName`" /V /FO LIST"

if ($RunNow) {
  Write-Host "==> Running task now..." -ForegroundColor Cyan
  schtasks /Run /TN $TaskName | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to run task via schtasks (exit=$LASTEXITCODE): $TaskName"
  }
}
