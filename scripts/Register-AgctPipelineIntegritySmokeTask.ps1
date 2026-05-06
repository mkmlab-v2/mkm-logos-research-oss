<#
.SYNOPSIS
  Register (or remove) a daily AGCT pipeline integrity smoke task.
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Agct_Pipeline_Integrity_Smoke_Daily",
    [string]$DailyAt = "07:40"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_agct_pipeline_integrity_smoke_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 07:40), got: $DailyAt"
}
$at = Get-Date -Hour ([int]$parts[0]) -Minute ([int]$parts[1]) -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $workspaceRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $at
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Daily AGCT integrity smoke for JSON race/format regression guards."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered scheduled task: $TaskName (Daily $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"

