<#
.SYNOPSIS
  Register weekly Scheduled Task: NVIDIA Inception partner credit / Gmail / Phoenix watch (CDP read-only).

.DESCRIPTION
  Runs Invoke-NvidiaInceptionPartnerCreditWeeklyWatch_v1.ps1 — tier_0 observation, no GPU.
  Default: Wednesday 09:30 local (Interactive — CDP Chrome profile when user session active).

.PARAMETER Remove
  Unregister the task.

.PARAMETER WednesdayAt
  Local time HH:mm (default: 09:30).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_NvidiaInception_PartnerCredit_Weekly",
    [string]$WednesdayAt = "09:30",
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
} elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
} else {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$runner = Join-Path $resolvedRoot "scripts\Invoke-NvidiaInceptionPartnerCreditWeeklyWatch_v1.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "REMOVED: $TaskName"
    exit 0
}

$parts = $WednesdayAt -split ':'
if ($parts.Count -lt 2) {
    throw "WednesdayAt must be HH:mm (e.g. 09:30), got: $WednesdayAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$resolvedRoot`"" `
    -WorkingDirectory $resolvedRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Wednesday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 25)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly: Gmail u/1 + Phoenix benefits + Lambda/GCP/Nebius/Azure CDP probes (read-only)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "REGISTERED: $TaskName (weekly Wednesday $WednesdayAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
Write-Host "Manual: powershell -File scripts\Invoke-NvidiaInceptionPartnerCreditWeeklyWatch_v1.ps1"
exit 0
