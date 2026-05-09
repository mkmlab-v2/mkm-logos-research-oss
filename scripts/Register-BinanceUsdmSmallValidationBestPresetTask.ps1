param(
  [string]$WorkspaceRoot = "",
  [string]$TaskName = "\MKM-BinanceUSDM-SmallValidation-BestPreset-2H",
  [int]$EveryHours = 2,
  [string]$StartTime = "00:45",
  [switch]$Force,
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
  if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  } else {
    $WorkspaceRoot = (Get-Location).Path
  }
}

if ($EveryHours -lt 1) {
  throw "-EveryHours must be >= 1"
}

$runner = Join-Path $WorkspaceRoot "scripts\Run-BinanceUsdmSmallValidationBestPreset.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner script not found: $runner"
}

if ($Force) {
  cmd /c "schtasks /Delete /TN `"$TaskName`" /F >nul 2>nul" | Out-Null
}

$action = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$user = "$env:USERDOMAIN\$env:USERNAME"

schtasks /Create /TN $TaskName /SC HOURLY /MO $EveryHours /ST $StartTime /TR $action /RU $user /RL LIMITED /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to register task via schtasks (exit=$LASTEXITCODE): $TaskName"
}

Write-Host "REGISTERED: $TaskName"
Write-Host "SCHEDULE: EVERY ${EveryHours}H FROM $StartTime (dry validation mode)"
Write-Host "RUN_MANUAL: schtasks /Run /TN `"$TaskName`""
Write-Host "QUERY: schtasks /Query /TN `"$TaskName`" /V /FO LIST"

if ($RunNow) {
  Write-Host "==> Running task now..." -ForegroundColor Cyan
  schtasks /Run /TN $TaskName | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to run task via schtasks (exit=$LASTEXITCODE): $TaskName"
  }
}
