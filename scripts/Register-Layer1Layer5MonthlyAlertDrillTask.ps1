<#
.SYNOPSIS
  Register (or remove) monthly Layer1/Layer5 alert drill scheduled task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Layer1Layer5_MonthlyAlertDrill",
    [string]$MonthlyAt = "10:00",
    [int]$DayOfMonth = 1,
    [switch]$LiveDispatch
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_layer1_layer5_monthly_alert_drill_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $MonthlyAt -split ':'
if ($parts.Count -lt 2) { throw "MonthlyAt must be HH:mm, got: $MonthlyAt" }

$psArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($LiveDispatch) { $psArgs += " -LiveDispatch" }
$tr = "powershell.exe $psArgs"

$createArgs = @(
    "/Create",
    "/F",
    "/TN", $TaskName,
    "/SC", "MONTHLY",
    "/D", "$DayOfMonth",
    "/ST", $MonthlyAt,
    "/TR", $tr
)
& schtasks.exe @createArgs | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Failed to register monthly task via schtasks.exe" }

Write-Host "Registered scheduled task: $TaskName (monthly day=$DayOfMonth $MonthlyAt, user=$env:USERNAME)"
