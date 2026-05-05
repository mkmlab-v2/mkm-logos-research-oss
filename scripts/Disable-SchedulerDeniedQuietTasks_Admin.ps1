# Requires elevated PowerShell (Task Scheduler tasks owned by SYSTEM / protected).
# Run: right-click PowerShell -> Run as administrator, then:
#   pwsh -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Disable-SchedulerDeniedQuietTasks_Admin.ps1

param([switch]$WhatIf)

$ErrorActionPreference = "Continue"

$isAdmin = try {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { $false }

if (-not $isAdmin) {
    Write-Host "ERROR: Run this script in an elevated PowerShell (Administrator)." -ForegroundColor Red
    Write-Host "From elevated shell:" -ForegroundColor Yellow
    Write-Host '  pwsh -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\Disable-SchedulerDeniedQuietTasks_Admin.ps1'
    exit 1
}

$taskNames = @(
    '\Athena_AutonomousLearning',
    '\Athena_AutonomousOrchestrator',
    '\Athena_DailySelfHygiene',
    '\Athena_DailyServerManagement',
    '\Athena_Jema12HealthCheck',
    '\Athena_SchedulerMetaAgent',
    '\Athena_SleepMode_Distillation',
    '\Athena_WebDocs_Collection',
    '\AutonomousReconnaissance',
    '\AutonomousTradingSystemCheck',
    '\CursorWorkspace_SelfHygiene',
    '\CursorWorkspace_TutorDaily4DAggregate',
    '\DimensionalProjection-EngineEval-Refresh-Daily',
    '\DimensionalProjection-LockVerify-Daily',
    '\IntelligentPowerManager',
    '\Jema12 KOSPI Alert 0830',
    '\JEMA12_Power_Saver_AutoStart',
    '\MKM_DailyMeta',
    '\MKM_Midnight_Prophecy',
    '\MKM_Morning_Reality_Flash',
    '\MKM_Titan_Mission_Watcher',
    '\MKM_TrackA_Commercialization_Daily',
    '\MKM_YouTube_Publish_Pipeline',
    '\Ops-Weekly-Digest',
    '\ProphecyRealtimeUpdater',
    '\QuadFusionDataCollectionDaily',
    '\VerifyTokenOptimization'
)

$ok = 0
$fail = New-Object System.Collections.Generic.List[string]

foreach ($tn in $taskNames) {
    if ($WhatIf) {
        Write-Host "[WhatIf] schtasks /Change /TN $tn /Disable"
        continue
    }
    schtasks.exe /Change /TN $tn /Disable 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ok++
    } else {
        $fail.Add($tn)
    }
}

Write-Host ("disabled_ok={0} failed={1}" -f $ok, $fail.Count)
if ($fail.Count -gt 0) {
    Write-Host "Failed tasks:" -ForegroundColor Yellow
    $fail | ForEach-Object { Write-Host "  $_" }
}
