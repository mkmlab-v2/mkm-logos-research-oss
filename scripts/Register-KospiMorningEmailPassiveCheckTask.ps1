<#
.SYNOPSIS
  Register daily 08:35 KST passive check after morning email digest (08:28).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM-Kospi-Morning-Email-PassiveCheck",
    [string]$DailyAt = "08:35",
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

$scriptPath = Join-Path $resolvedRoot "scripts\check_kospi_morning_email_digest_passive_v1.py"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Missing: $scriptPath"
}

$action = New-ScheduledTaskAction -Execute "py" -Argument "`"$scriptPath`"" -WorkingDirectory $resolvedRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "REMOVED: $TaskName"
    exit 0
}

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "REGISTERED: $TaskName daily $DailyAt at $resolvedRoot"
exit 0
