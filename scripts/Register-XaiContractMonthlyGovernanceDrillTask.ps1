<#
.SYNOPSIS
  Register or remove a monthly scheduled task for XAI governance drill.

.DESCRIPTION
  Runs scripts/run_xai_contract_monthly_governance_drill_v1.ps1 once per month.
#>
param(
  [switch]$Remove,
  [string]$TaskName = "MKM_XAI_Contract_Monthly_Governance_Drill",
  [string]$WorkspaceRoot = "C:\workspace",
  [string]$At = "08:10",
  [int]$DayOfMonth = 1,
  [double]$NormalMinPassRate = 0.95,
  [double]$NormalCriticalPassRate = 0.85,
  [double]$DrillMinPassRate = 1.1,
  [double]$DrillCriticalPassRate = 1.05
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Invoke-XaiContractMonthlyGovernanceDrill.ps1"

if ($Remove) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task (if existed): $TaskName"
  exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
  throw "Runner not found: $runner"
}

$atTime = [DateTime]::ParseExact($At, "HH:mm", $null)
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$runner"" -WorkspaceRoot ""$WorkspaceRoot"""

# Use schtasks for monthly trigger compatibility across Windows editions.
$createArgs = @(
  "/Create",
  "/F",
  "/TN", $TaskName,
  "/SC", "MONTHLY",
  "/D", $DayOfMonth,
  "/ST", $At,
  "/TR", "powershell.exe $argLine"
)
schtasks.exe @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to create monthly scheduled task: $TaskName"
}

Write-Host "Registered: $TaskName (monthly day $DayOfMonth at $At via schtasks)"
Write-Host "Runner: $runner"
