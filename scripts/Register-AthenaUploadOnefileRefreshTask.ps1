<#
.SYNOPSIS
  Register (or remove) a daily task that refreshes ATHENA upload onefile.

.DESCRIPTION
  Runs scripts/build_athena_upload_onefile_latest.py once per day so
  docs/final/artifacts/ATHENA_UPLOAD_ONEFILE_LATEST.md stays current for
  Gemini/NotebookLM upload.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "AthenaUploadOnefileRefreshDaily",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$PythonExe = "py",
    [string]$At = "00:30"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "scripts\build_athena_upload_onefile_latest.py"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Builder script not found: $scriptPath"
}

$time = [DateTime]::ParseExact($At, "HH:mm", $null)
$argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"& { Set-Location -LiteralPath '$WorkspaceRoot'; $PythonExe '$scriptPath' }`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Refresh ATHENA_UPLOAD_ONEFILE_LATEST.md daily for Gemini/NotebookLM."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (daily at $At, user=$env:USERNAME)"
Write-Host "Builder: $scriptPath"
