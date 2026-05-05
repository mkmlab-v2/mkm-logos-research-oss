<#
.NOTES
  For single daily chain (Fragility + Forward + Logos + ops dashboard), prefer
  Register-TrackCMacroDailyFusionTask.ps1. Running this task AND fusion in parallel
  duplicates Fragility work.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$TaskName = "MKM-Fragility-MacroRisk-Daily",

    [Parameter(Mandatory = $false)]
    [string]$RunAt = "07:20",

    [switch]$PreferFred,
    [switch]$Remove,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$dailyScript = Join-Path $PSScriptRoot "Invoke-FragilityMacroRiskDaily.ps1"
if (-not (Test-Path -LiteralPath $dailyScript)) {
    throw "Required script not found: $dailyScript"
}

try {
    $runTime = [DateTime]::ParseExact($RunAt, "HH:mm", $null)
}
catch {
    throw "RunAt must be HH:mm format, e.g. 07:20"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$dailyScript`""
if ($PreferFred) { $argument += " -PreferFred" }

$actionParams = @{
    Execute = "powershell.exe"
    Argument = $argument
}
try {
    $action = New-ScheduledTaskAction @actionParams -WorkingDirectory $repoRoot
}
catch {
    $action = New-ScheduledTaskAction @actionParams
}

$trigger = New-ScheduledTaskTrigger -Daily -At $runTime
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "run_at=$RunAt"
Write-Output ("prefer_fred={0}" -f [bool]$PreferFred)

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
