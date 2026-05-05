param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$TaskName = "\MKM-Trading-Execution-Chain-Once",
  [string]$RunTime = "23:59",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$runner = Join-Path $WorkspaceRoot "scripts\Run-TradingExecutionChainOnce.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner script not found: $runner"
}

# Future one-time trigger to avoid accidental auto run; task is intended for manual /Run.
$futureDate = "2099/12/31"
$action = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$runner`""
$user = "$env:USERDOMAIN\$env:USERNAME"

if ($Force) {
  try {
    schtasks /Delete /TN $TaskName /F | Out-Null
  } catch { }
}

schtasks /Create /TN $TaskName /SC ONCE /SD $futureDate /ST $RunTime /TR $action /RU $user /RL LIMITED /F | Out-Null

Write-Host "REGISTERED: $TaskName"
Write-Host "TRIGGER: ONCE $futureDate $RunTime (manual /Run intended)"
Write-Host "RUN_MANUAL: schtasks /Run /TN `"$TaskName`""
Write-Host "QUERY: schtasks /Query /TN `"$TaskName`" /V /FO LIST"

