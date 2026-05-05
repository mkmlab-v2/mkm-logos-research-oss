<#
.NOTES
  Prefer Register-TrackCMacroDailyFusionTask.ps1 for daily ops (uses -SkipFragilityChain).
  Parallel registration with MKM-Fragility-MacroRisk-Daily duplicates Fragility unless
  this script is always run with -SkipFragilityChain (fusion already ran Fragility).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MacroRiskForwardDailyChain",
    [string]$DailyAt = "07:25",
    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h",
    [switch]$SkipFragilityChain,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "run_macro_risk_forward_daily_chain_v1.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Required script not found: $scriptPath"
}

$timeParts = $DailyAt.Split(":")
if ($timeParts.Count -ne 2) {
    throw "DailyAt must be HH:mm format, got: $DailyAt"
}
$hour = [int]$timeParts[0]
$minute = [int]$timeParts[1]
if ($hour -lt 0 -or $hour -gt 23 -or $minute -lt 0 -or $minute -gt 59) {
    throw "DailyAt out of range: $DailyAt"
}

$argList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$scriptPath`"",
    "-AssetScope", $AssetScope,
    "-Horizon", $Horizon
)
if ($PreferFred) { $argList += "-PreferFred" }
if ($SkipFragilityChain) { $argList += "-SkipFragilityChain" }

$psArgs = $argList -join " "
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($hour).AddMinutes($minute))
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable

if ($DryRun) {
    Write-Host "[register-forward-task] DRY_RUN"
    Write-Host "TaskName: $TaskName"
    Write-Host "DailyAt: $DailyAt"
    Write-Host "Command: powershell.exe $psArgs"
    exit 0
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Run Macro Risk forward-testing daily chain (preregister + forward log + weekly summary)." `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName
Write-Host "[register-forward-task] PASS"
Write-Host "[register-forward-task] task_name=$TaskName"
Write-Host "[register-forward-task] state=$($task.State)"
Write-Host "[register-forward-task] command=powershell.exe $psArgs"

