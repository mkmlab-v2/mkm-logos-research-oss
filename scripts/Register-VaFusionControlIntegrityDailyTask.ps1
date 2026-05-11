<#
.SYNOPSIS
  Register (or remove) a daily scheduled task for the VA→fusion→integrity audit chain.

.DESCRIPTION
  Runs scripts/Run-VaFusionControlIntegrityChain_v1.ps1 once per day (default 07:35 local).
  B-track only; see CONSTITUTION §3.8.4.
#>
param(
    [switch]$Remove,
    [string]$TaskName = 'MKM-VaFusionControlIntegrity-Daily',
    [string]$DailyAt = '07:35',
    [switch]$EnableCooldown,
    [switch]$WriteState
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = 'C:\workspace'
$runner = Join-Path $workspaceRoot 'scripts\Run-VaFusionControlIntegrityChain_v1.ps1'

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
    throw "DailyAt must be HH:mm (e.g. 07:35), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$runnerArgs = @(
    '-NoProfile',
    '-WindowStyle', 'Hidden',
    '-ExecutionPolicy', 'Bypass',
    '-File', "`"$runner`""
)
if ($EnableCooldown) { $runnerArgs += '-EnableCooldown' }
if ($WriteState) { $runnerArgs += '-WriteState' }
$argLine = $runnerArgs -join ' '

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = 'B-track VA trajectory, cross-lens fusion stub, fusion control integrity audit (Run-VaFusionControlIntegrityChain_v1.ps1).'

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName at $DailyAt daily (user=$env:USERNAME, workspace: $workspaceRoot)"
Write-Host "Runner: $runner"
