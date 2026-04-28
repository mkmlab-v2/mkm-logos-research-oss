<#
.SYNOPSIS
  Register (or remove) a monthly Scheduled Task for live PointerGuard P0 drill.

.PARAMETER Remove
  Unregister the task.

.PARAMETER DryRun
  Print registration details without creating/removing task.
#>
param(
    [switch]$Remove,
    [switch]$DryRun,
    [string]$TaskName = "MKM_PointerGuard_Monthly_P0_Drill",
    [int]$DayOfMonth = 1,
    [string]$AtTime = "07:10"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_pointerguard_monthly_maintenance_chain_v1.ps1"

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
    throw "AtTime must be HH:mm (e.g. 07:10), got: $AtTime"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""
$description = "Monthly live PointerGuard drill + maintenance report chain."

if ($DryRun) {
    Write-Host "[DryRun] TaskName: $TaskName"
    Write-Host "[DryRun] Trigger : Monthly day=$DayOfMonth at $AtTime"
    Write-Host "[DryRun] Runner  : $runner"
    Write-Host "[DryRun] Command : powershell.exe $argLine"
    Write-Host "[DryRun] Desc    : $description"
    exit 0
}

$startTime = "{0:D2}:{1:D2}" -f $hour, $minute
$taskRun = "powershell.exe $argLine"
$createArgs = @(
    "/Create",
    "/F",
    "/TN", $TaskName,
    "/SC", "MONTHLY",
    "/D", "$DayOfMonth",
    "/ST", $startTime,
    "/TR", "`"$taskRun`"",
    "/RL", "LIMITED",
    "/RU", $env:USERNAME
)
$cp = Start-Process -FilePath "schtasks.exe" -ArgumentList $createArgs -NoNewWindow -Wait -PassThru
if ($cp.ExitCode -ne 0) {
    throw "Failed to register scheduled task via schtasks.exe (exit=$($cp.ExitCode))"
}

Write-Host "Registered scheduled task: $TaskName (monthly day=$DayOfMonth at $AtTime, user=$env:USERNAME)"
Write-Host "Runner: $runner"
