[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$TaskName = "MKM-n8n-Service",

    [switch]$Remove,
    [switch]$StartNow,
    [int]$StartupDelaySec = 45,
    [int]$HealthTimeoutSec = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$guardScript = Join-Path $PSScriptRoot "Run-N8nServiceGuardV1.ps1"
if (-not (Test-Path -LiteralPath $guardScript)) {
    throw "Required script not found: $guardScript"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$guardScript`" -StartupDelaySec $StartupDelaySec -HealthTimeoutSec $HealthTimeoutSec"
try {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $repoRoot
}
catch {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs
}
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "startup_delay_sec=$StartupDelaySec"
Write-Output "health_timeout_sec=$HealthTimeoutSec"
Write-Output "guard_script=$guardScript"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
