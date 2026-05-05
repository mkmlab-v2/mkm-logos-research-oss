<#
.SYNOPSIS
  Register (or remove) daily Scheduled Task for ATHENA onefile NotebookLM push.

.DESCRIPTION
  Executes scripts/Push-AthenaUploadOnefileToNotebooklm.ps1 daily.
  Intended to run after onefile refresh task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "AthenaUploadOnefileNotebooklmPushDaily",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$NotebookId = "347e5cbe-0ade-4615-9aac-8747d4fa644e",
    [string]$At = "00:40"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $WorkspaceRoot "scripts\Push-AthenaUploadOnefileToNotebooklm.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$time = [DateTime]::ParseExact($At, "HH:mm", $null)
$argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`" -NotebookId `"$NotebookId`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Daily push of ATHENA_UPLOAD_ONEFILE_LATEST to NotebookLM."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName (daily at $At, user=$env:USERNAME)"
Write-Host "Runner: $runner"
