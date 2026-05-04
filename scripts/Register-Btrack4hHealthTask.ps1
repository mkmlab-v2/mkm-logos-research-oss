<#
.SYNOPSIS
  Register (or remove) a scheduled task that runs a lightweight B-Track artifact health check every N hours.

.DESCRIPTION
  Runs: py scripts/check_btrack_4h_health_v1.py
  Default: every 4 hours, starting a few minutes from registration time.
  Does NOT run the full run_btrack_daily_hypothesis_chain.ps1 (Fact-Lock: thin probe only).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Scheduled task name (default: MKM_BTrack_4h_Health).

.PARAMETER IntervalHours
  Repetition interval in hours (default: 4).

.PARAMETER WorkspaceRoot
  Repo root (default: C:\workspace).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_BTrack_4h_Health",
    [int]$IntervalHours = 4,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\check_btrack_4h_health_v1.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task (if existed): $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($IntervalHours -lt 1 -or $IntervalHours -gt 24) {
    throw "IntervalHours must be between 1 and 24, got: $IntervalHours"
}

$start = (Get-Date).AddMinutes(2)
$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Set-Location -LiteralPath '$WorkspaceRoot'; py '$runner'`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Once -At $start `
    -RepetitionInterval (New-TimeSpan -Hours $IntervalHours) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Every ${IntervalHours}h: B-Track artifact JSON health (hypothesis, score, hit-rate eval)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (every $IntervalHours hours from $start)"
Write-Host "Runner: $runner"
