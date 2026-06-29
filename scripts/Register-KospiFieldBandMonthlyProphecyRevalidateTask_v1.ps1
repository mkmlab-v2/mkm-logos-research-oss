<#
.SYNOPSIS
  Register monthly Scheduled Task: KOSPI Field band prophecy revalidate (post L4 sign).

.PARAMETER Remove
  Unregister the task.

.PARAMETER DayOfMonth
  Default: 2 (after month open).

.PARAMETER AtTime
  Local HH:mm (default: 09:30).
#>
param(
    [switch]$Remove,
    [switch]$DryRun,
    [string]$TaskName = "MKM_KospiFieldBand_MonthlyProphecyRevalidate",
    [int]$DayOfMonth = 2,
    [string]$AtTime = "09:30",
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Run-KospiFieldBandMonthlyProphecyRevalidate_v1.ps1"

if ($Remove) {
    if ($DryRun) {
        Write-Host "[DryRun] Would remove scheduled task: $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $AtTime -split ':'
if ($parts.Count -lt 2) {
    throw "AtTime must be HH:mm, got: $AtTime"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$startTime = "{0:D2}:{1:D2}" -f $hour, $minute

$cmd = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""

if ($DryRun) {
    Write-Host "[DryRun] TaskName: $TaskName"
    Write-Host "[DryRun] Trigger : Monthly day=$DayOfMonth at $AtTime"
    Write-Host "[DryRun] Runner  : $runner"
    Write-Host "[DryRun] Command : $cmd"
    Write-Host "SSOT tier: tier4_solo_intentional_keep (mkm_scheduler_solo_core_stack_v1.json)"
    exit 0
}

$createArgs = @(
    "/Create",
    "/F",
    "/TN", $TaskName,
    "/SC", "MONTHLY",
    "/D", "$DayOfMonth",
    "/ST", $startTime,
    "/TR", "`"$cmd`"",
    "/RL", "LIMITED",
    "/RU", $env:USERNAME
)
$cp = Start-Process -FilePath "schtasks.exe" -ArgumentList $createArgs -NoNewWindow -Wait -PassThru
if ($cp.ExitCode -ne 0) {
    throw "Failed to register scheduled task via schtasks.exe (exit=$($cp.ExitCode))"
}

Write-Host "Registered scheduled task: $TaskName (monthly day=$DayOfMonth at $AtTime)"
Write-Host "Runner: $runner"
Write-Host "SSOT tier: tier4_solo_intentional_keep (mkm_scheduler_solo_core_stack_v1.json)"
