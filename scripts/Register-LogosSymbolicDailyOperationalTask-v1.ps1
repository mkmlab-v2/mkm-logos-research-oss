param(
  [string]$TaskName = "MKM-LogosSymbolic-Daily-Operational-Bundle",
  [string]$At = "08:40",
  [string]$WorkspaceRoot = "C:\workspace",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$bundleScript = Join-Path $WorkspaceRoot "scripts\run_logos_symbolic_daily_operational_bundle_v1.ps1"
if (-not (Test-Path -LiteralPath $bundleScript)) {
  throw "Missing bundle script: $bundleScript"
}

$tr = "pwsh -NoProfile -ExecutionPolicy Bypass -File `"$bundleScript`""
$createCmd = "schtasks /Create /TN `"$TaskName`" /SC DAILY /ST $At /TR `"$tr`" /F"
$queryCmd = "schtasks /Query /TN `"$TaskName`" /V /FO LIST"

Write-Host "Create command:" -ForegroundColor Cyan
Write-Host $createCmd
Write-Host "Query command:" -ForegroundColor Cyan
Write-Host $queryCmd

if ($DryRun) {
  Write-Host "DryRun: no task changes applied." -ForegroundColor Yellow
  exit 0
}

cmd /c $createCmd | Out-Host
if ($LASTEXITCODE -ne 0) {
  throw "schtasks create failed with exit code $LASTEXITCODE"
}

cmd /c $queryCmd | Out-Host
if ($LASTEXITCODE -ne 0) {
  throw "schtasks query failed with exit code $LASTEXITCODE"
}

Write-Host "OK: Task registered -> $TaskName" -ForegroundColor Green
