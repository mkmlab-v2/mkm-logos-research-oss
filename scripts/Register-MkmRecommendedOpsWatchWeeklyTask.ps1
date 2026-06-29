<#
.SYNOPSIS
  Register weekly Sunday recommended ops watch (Cursor Origin + session guard + GeekNews).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_RecommendedOpsWatch_Weekly",
    [string]$SundayAt = "09:00",
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

$scriptPath = Join-Path $resolvedRoot "scripts\Invoke-MkmRecommendedOpsWatch_v1.ps1"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing: $scriptPath"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -WorkspaceRoot `"$resolvedRoot`" -SkipKospiPassive" `
    -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $SundayAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "REMOVED: $TaskName"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "REGISTERED: $TaskName Sunday $SundayAt at $resolvedRoot"
exit 0
