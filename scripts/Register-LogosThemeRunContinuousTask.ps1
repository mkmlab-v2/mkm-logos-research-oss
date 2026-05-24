#Requires -Version 5.1
<#
.SYNOPSIS
  Register Windows Scheduled Task for LOGOS-THEME-RUN continuous (expand + integrate).

.PARAMETER EveryMinutes
  Repeat interval (default 5). Minimum 5. Idle ticks skip heavy integrate when backlog empty and theme count unchanged.

.PARAMETER UseGeminiExpand
  Forward --use-gemini to backlog expand when API key is available.

.PARAMETER RunWhenLoggedOff
  Use S4U principal (requires admin registration). Use when host should run without interactive login.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Register-LogosThemeRunContinuousTask.ps1 -EveryMinutes 120

.EXAMPLE
  Remove: -Remove
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM-LogosThemeRunContinuous",
    [int]$EveryMinutes = 5,
    [string]$WorkspaceRoot = "",
    [switch]$UseGeminiExpand,
    [int]$ExpandMaxPerRun = 5,
    [switch]$AutoRefillSeed = $true,
    [int]$SeedRefillBatch = 10,
    [switch]$SkipExpand,
    [switch]$SkipDeploy,
    [switch]$RunWhenLoggedOff,
    [switch]$DryRun,
    [switch]$Remove,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$runner = Join-Path $repoRoot "scripts\Invoke-LogosThemeRunContinuous_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Missing runner: $runner"
}
if ($EveryMinutes -lt 5 -or $EveryMinutes -gt 1440) {
    throw "EveryMinutes must be 5..1440"
}

$argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -WorkspaceRoot `"$repoRoot`""
if ($UseGeminiExpand) { $argument += " -UseGeminiExpand" }
$argument += " -ExpandMaxPerRun $ExpandMaxPerRun"
if ($AutoRefillSeed) {
    $argument += " -AutoRefillSeed -SeedRefillBatch $SeedRefillBatch"
}
if ($SkipExpand) { $argument += " -SkipExpand" }
if ($SkipDeploy) { $argument += " -SkipDeploy" }

if ($DryRun) {
    Write-Output "scheduled_task: DRY_RUN"
    Write-Output "task_name=$TaskName every_minutes=$EveryMinutes"
    Write-Output "argument=$argument"
    Write-Output "runner=$runner"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3652)

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

if ($RunWhenLoggedOff) {
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
} else {
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
}

$description = "LOGOS-THEME-RUN: backlog expand + integrate (NON_GATING). STOP: docs/research/logos_metaphor_db_v1/LOGOS_THEME_RUN.stop"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "every_minutes=$EveryMinutes"
Write-Output "stop_file=docs/research/logos_metaphor_db_v1/LOGOS_THEME_RUN.stop"
Write-Output "verify=scripts/Verify-LogosThemeRunScheduledTask_v1.ps1"

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
