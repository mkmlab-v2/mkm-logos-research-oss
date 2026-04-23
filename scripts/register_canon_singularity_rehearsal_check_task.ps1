# Register (or remove) a daily scheduled task for rehearsal status check.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\register_canon_singularity_rehearsal_check_task.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\register_canon_singularity_rehearsal_check_task.ps1 -DailyAt "06:50" -AppendHistory

param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CanonSingularity_RehearsalCheck",
    [string]$DailyAt = "06:50",
    [switch]$AppendHistory,
    [switch]$AutoRunStrictOnAlert,
    [switch]$NoAppendHistory,
    [switch]$NoAutoRunStrictOnAlert,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$checker = Join-Path $workspaceRoot "scripts\check_canon_singularity_rehearsal_status.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $checker)) {
    throw "Checker script not found: $checker"
}

$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$checker`""
)

$effectiveAppendHistory = $true
if ($NoAppendHistory) {
    $effectiveAppendHistory = $false
} elseif ($AppendHistory) {
    $effectiveAppendHistory = $true
}

$effectiveAutoRunStrictOnAlert = $true
if ($NoAutoRunStrictOnAlert) {
    $effectiveAutoRunStrictOnAlert = $false
} elseif ($AutoRunStrictOnAlert) {
    $effectiveAutoRunStrictOnAlert = $true
}

if ($effectiveAppendHistory) {
    $runnerArgs += "-AppendHistory"
}
if ($effectiveAutoRunStrictOnAlert) {
    $runnerArgs += "-AutoRunStrictOnAlert"
}
$runnerArgString = ($runnerArgs -join " ")

if ($PrintOnly) {
    Write-Host "PrintOnly: no task registration performed."
    Write-Host "TaskName: $TaskName"
    Write-Host "DailyAt: $DailyAt"
    Write-Host "AppendHistory: $effectiveAppendHistory"
    Write-Host "AutoRunStrictOnAlert: $effectiveAutoRunStrictOnAlert"
    Write-Host "RunnerArgs: $runnerArgString"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $runnerArgString `
    -WorkingDirectory $workspaceRoot

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:50), got: $DailyAt"
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
$description = "Run canon rehearsal check and status snapshot. AppendHistory=$effectiveAppendHistory AutoRunStrictOnAlert=$effectiveAutoRunStrictOnAlert"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Checker: $checker"

