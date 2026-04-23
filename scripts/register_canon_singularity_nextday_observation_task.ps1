# Register (or remove) a daily scheduled task for nextday no-touch observation report.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\register_canon_singularity_nextday_observation_task.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\register_canon_singularity_nextday_observation_task.ps1 -DailyAt "07:20"

param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CanonSingularity_NextdayObservation",
    [string]$DailyAt = "07:20",
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$builder = Join-Path $workspaceRoot "scripts\core\build_canon_singularity_nextday_observation_report_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $builder)) {
    throw "Nextday observation builder not found: $builder"
}

$runnerArgs = @($builder)
$runnerArgString = ($runnerArgs -join " ")

if ($PrintOnly) {
    Write-Host "PrintOnly: no task registration performed."
    Write-Host "TaskName: $TaskName"
    Write-Host "DailyAt: $DailyAt"
    Write-Host "RunnerArgs: $runnerArgString"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "py.exe" `
    -Argument $runnerArgString `
    -WorkingDirectory $workspaceRoot

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 07:20), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Build canon nextday no-touch observation report daily."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Builder: $builder"

