<#
.SYNOPSIS
  Register (or remove) monthly external anchor downgrade-recovery drill task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_ExternalAnchor_DowngradeRecovery_MonthlyDrill",
    [string]$MonthlyAt = "10:30",
    [int]$DayOfMonth = 1
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_external_anchor_downgrade_recovery_monthly_drill_v1.ps1"

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

$psArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""
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
Write-Host "Runner: $runner"
