[CmdletBinding()]
param(
    [string]$TaskName = "MKM-Orchestrator-GoStability-15m",
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$EveryMinutes = 15,
    [switch]$SkipOrchestratorRun,
    [switch]$EnableAutoDemotion,
    [switch]$EnableAutoPromotion,
    [int]$AutoPromotionMinGoStreak = 3,
    [switch]$Remove,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runner = Join-Path $WorkspaceRoot "scripts\run_mkm_orchestrator_go_stability_cycle_v1.ps1"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}
if ($EveryMinutes -lt 1) {
    throw "EveryMinutes must be >= 1"
}

$argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$WorkspaceRoot`""
if ($SkipOrchestratorRun) { $argLine += " -SkipOrchestratorRun" }
if ($EnableAutoDemotion) { $argLine += " -EnableAutoDemotion" }
if ($EnableAutoPromotion) { $argLine += " -EnableAutoPromotion -AutoPromotionMinGoStreak $AutoPromotionMinGoStreak" }

$actionParams = @{
    Execute = "powershell.exe"
    Argument = $argLine
}
try {
    $action = New-ScheduledTaskAction @actionParams -WorkingDirectory $WorkspaceRoot
}
catch {
    $action = New-ScheduledTaskAction @actionParams
}

$trigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "MKM orchestrator GO stability watcher (periodic transition detection)."

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "every_minutes=$EveryMinutes"
Write-Output "runner=$runner"
Write-Output ("skip_orchestrator_run={0}" -f [bool]$SkipOrchestratorRun)
Write-Output ("enable_auto_demotion={0}" -f [bool]$EnableAutoDemotion)
Write-Output ("enable_auto_promotion={0}" -f [bool]$EnableAutoPromotion)
Write-Output ("auto_promotion_min_go_streak={0}" -f $AutoPromotionMinGoStreak)

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
