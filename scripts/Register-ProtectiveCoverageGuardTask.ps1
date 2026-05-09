param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "\MKM-Protective-Coverage-Guard-15min",
  [int]$IntervalMinutes = 15,
  [switch]$Force,
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($IntervalMinutes -lt 5) {
  throw "-IntervalMinutes must be >= 5"
}

$runner = Join-Path $WorkspaceRoot "scripts\Run-ProtectiveCoverageGuardTask.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner script not found: $runner"
}

if ($Force) {
  cmd /c "schtasks /Delete /TN `"$TaskName`" /F >nul 2>nul" | Out-Null
}

$startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
$action = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$user = "$env:USERDOMAIN\$env:USERNAME"

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /ST $startTime /TR $action /RU $user /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to register task via schtasks (exit=$LASTEXITCODE): $TaskName"
}

Write-Host "REGISTERED: $TaskName"
Write-Host "SCHEDULE: EVERY ${IntervalMinutes}min FROM $startTime"
Write-Host "RUN_MANUAL: schtasks /Run /TN `"$TaskName`""
Write-Host "QUERY: schtasks /Query /TN `"$TaskName`" /V /FO LIST"

if ($RunNow) {
  Write-Host "==> Running task now..." -ForegroundColor Cyan
  schtasks /Run /TN $TaskName | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to run task via schtasks (exit=$LASTEXITCODE): $TaskName"
  }
}
