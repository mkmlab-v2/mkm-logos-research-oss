<#
.SYNOPSIS
  Register (or remove) a daily Scheduled Task for Compression Shadow Auditor (RQ-018).

.DESCRIPTION
  Runs: scripts/Run-CompressionShadowAuditor_v1.ps1 (default: audit frozen artifacts + pytest).
  Does not refresh full bench unless -RefreshLossPatterns is added to the registered action.

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_Compression_ShadowAuditor_Daily

.PARAMETER DailyAt
  Local time HH:mm (default: 02:30).

.PARAMETER RefreshLossPatterns
  Pass -RefreshLossPatterns to the nightly runner (regenerates loss patterns; no full bench).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Compression_ShadowAuditor_Daily",
    [string]$DailyAt = "02:30",
    [switch]$RefreshLossPatterns
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\Run-CompressionShadowAuditor_v1.ps1"

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
    throw "DailyAt must be HH:mm (e.g. 02:30), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$workspaceRoot`""
if ($RefreshLossPatterns) {
    $argLine += " -RefreshLossPatterns"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily: compression shadow auditor (pytest ultra artifacts + KPI/loss queue). B-track only."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
if ($RefreshLossPatterns) {
    Write-Host "Note: task uses -RefreshLossPatterns."
}
