#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: MKM Doc Sync Safe (local C-layer; cloud Automations 대체).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_DocSync_Safe_Weekly

.PARAMETER SundayAt
  Local time HH:mm (default 09:00).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_DocSync_Safe_Weekly",
    [string]$SundayAt = "09:00",
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$runner = Join-Path $resolvedRoot "scripts\Invoke-MkmDocSyncSafe_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$existing = schtasks /Query /TN $TaskName /FO LIST 2>$null
if ($LASTEXITCODE -eq 0 -and ($existing -match 'Ready|Running')) {
    Write-Host "Already registered (Ready): $TaskName"
    exit 0
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) { throw "SundayAt must be HH:mm, got: $SundayAt" }
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$resolvedRoot`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly MKM Doc Sync Safe (local). SSOT: scripts/Invoke-MkmDocSyncSafe_v1.ps1"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (Sunday $SundayAt)"
Write-Host "Runner: $runner"
exit 0
