<#
.SYNOPSIS
  Register (or remove) daily scheduled task for Layer1/Layer5 governance chain.

.DESCRIPTION
  Runs scripts/run_layer1_layer5_governance_daily_v1.ps1 once daily.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Layer1Layer5_Governance_Daily",
    [string]$DailyAt = "08:00",
    [int]$SampleSize = 50,
    [int]$Seed = 42,
    [int]$MinApprovedSamples = 50
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_layer1_layer5_governance_daily_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ':'
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 08:00), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -SampleSize $SampleSize -Seed $Seed -MinApprovedSamples $MinApprovedSamples"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily governance verification for Layer1/Layer5 integrated gate and readiness artifact."
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
