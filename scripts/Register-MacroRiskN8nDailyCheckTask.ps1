[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$TaskName = "MKM-MacroRisk-N8n-DailyCheck",

    [Parameter(Mandatory = $false)]
    [string]$RunAt = "09:00",

    [switch]$Remove,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$dailyScript = Join-Path $PSScriptRoot "Run-MacroRiskN8nDailyCheck.ps1"
if (-not (Test-Path -LiteralPath $dailyScript)) {
    throw "Required script not found: $dailyScript"
}

try {
    $runTime = [DateTime]::ParseExact($RunAt, "HH:mm", $null)
}
catch {
    throw "RunAt must be HH:mm format, e.g. 09:00"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$actionParams = @{
    Execute          = "powershell.exe"
    Argument         = "-NoProfile -ExecutionPolicy Bypass -File `"$dailyScript`""
}
try {
    $action = New-ScheduledTaskAction @actionParams -WorkingDirectory $repoRoot
}
catch {
    $action = New-ScheduledTaskAction @actionParams
}

$trigger = New-ScheduledTaskTrigger -Daily -At $runTime
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "run_at=$RunAt"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
