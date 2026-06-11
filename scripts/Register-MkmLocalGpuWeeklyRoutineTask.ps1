#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Scheduled Task: local GPU routine (CPU gates + optional RTX MusicGen).

.PARAMETER Remove
  Unregister the task.

.PARAMETER TaskName
  Default: MKM_Local_Gpu_Weekly_Routine

.PARAMETER SundayAt
  Local time HH:mm (default 20:00 — after compression governance 07:00 / gpu bundle 08:00).

.PARAMETER IncludeAudioGenerate
  Pass -IncludeAudioGenerate to runner (MusicGen on local RTX; ~15–25 min).

.PARAMETER IncludeMusicGenLoop32Smoke
  Pass -IncludeMusicGenLoop32Smoke (32s hub loop + audio gate; ~7–10 min CUDA).

.PARAMETER IncludeGpuRecommendedBundle
  Also run Control-Integrity oracle + Pack 0-B pytest after audio (longer).

.PARAMETER IncludeMediaThinSliceBake
  Pass -IncludeMediaThinSliceBake to runner (ffmpeg WebM + media observability; pairs with audio).
#>
param(
    [switch]$Remove,
    [string]$TaskName = "MKM_Local_Gpu_Weekly_Routine",
    [string]$SundayAt = "20:00",
    [switch]$IncludeAudioGenerate,
    [switch]$IncludeMusicGenLoop32Smoke,
    [switch]$IncludeMediaThinSliceBake,
    [switch]$IncludeGpuRecommendedBundle,
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

$runner = Join-Path $resolvedRoot "scripts\Run-LocalGpuWeeklyRoutine_v1.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$parts = $SundayAt -split ':'
if ($parts.Count -lt 2) { throw "SundayAt must be HH:mm, got: $SundayAt" }
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$at = Get-Date -Hour $hour -Minute $minute -Second 0

$argLine = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`""
if ($IncludeAudioGenerate) { $argLine += " -IncludeAudioGenerate" }
if ($IncludeMusicGenLoop32Smoke) { $argLine += " -IncludeMusicGenLoop32Smoke" }
if ($IncludeMediaThinSliceBake) { $argLine += " -IncludeMediaThinSliceBake" }
if ($IncludeGpuRecommendedBundle) { $argLine += " -IncludeGpuRecommendedBundle" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $argLine `
    -WorkingDirectory $resolvedRoot

$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Sunday -At $at

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$description = "Weekly local GPU routine: Azure sync + Kaggle gate + audio counsel chain; optional RTX MusicGen. Workspace: $resolvedRoot"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered: $TaskName (Sunday $SundayAt)"
Write-Host "Runner: $runner"
if ($IncludeAudioGenerate) { Write-Host "Includes: -IncludeAudioGenerate (local CUDA MusicGen)" }
if ($IncludeMusicGenLoop32Smoke) { Write-Host "Includes: -IncludeMusicGenLoop32Smoke (32s loop + gate)" }
if ($IncludeMediaThinSliceBake) { Write-Host "Includes: -IncludeMediaThinSliceBake (ffmpeg WebM + media observability)" }
if ($IncludeGpuRecommendedBundle) { Write-Host "Includes: -IncludeGpuRecommendedBundle" }
