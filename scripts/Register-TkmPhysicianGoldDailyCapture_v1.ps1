<#
.SYNOPSIS
  Register daily Task Scheduler job for physician_gold capture (08:00 local).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-TkmPhysicianGoldDailyCapture_v1.ps1
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-TkmPhysicianGold-DailyCapture",
    [string]$RunAt = "08:00",
    [switch]$DryRun,
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

$runner = Join-Path $PSScriptRoot "run_tkm_physician_gold_daily_capture_v1.py"
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing: $runner" }

$repoRoot = Split-Path -Parent $PSScriptRoot
$argument = "-NoProfile -ExecutionPolicy Bypass -Command `"& py '$runner'`""

if ($DryRun) {
    Write-Output "scheduled_task: DRY_RUN would_register=$TaskName at=$RunAt"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName) at=$RunAt"

if ($StartNow) {
    & py $runner
    if ($LASTEXITCODE -ne 0) { throw "daily capture failed exit $LASTEXITCODE" }
    Write-Output "daily_capture: ok"
}
