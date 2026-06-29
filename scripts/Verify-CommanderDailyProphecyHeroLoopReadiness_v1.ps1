#Requires -Version 5.1
<#
.SYNOPSIS
  Verify Commander daily prophecy hero loop tasks + SSOT scripts.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$tasks = @(
    @{ Name = "MKM-BTrack-DailyHypothesis-Chain"; Required = $true }
    @{ Name = "MKM-Prophecy-Daily-Eval-Report"; Required = $true }
    @{ Name = "MKM-Research-Morning-Prediction-Registry"; Required = $true }
    @{ Name = "MKM-Telegram-Minimal-Daily-Digest"; Required = $true }
    @{ Name = "MKM-Prophecy-Panel-24h-Alerts"; Required = $false }
    @{ Name = "GeneralProphecyDailyQueueV1"; Required = $false }
    @{ Name = "MKM-Commander-Evening-Briefing-Score"; Required = $true }
)

$scripts = @(
    "scripts\Invoke-CommanderDailyProphecyHeroLoop_v1.ps1"
    "scripts\build_research_morning_prediction_registry_v1.py"
    "scripts\score_research_evening_predictions_v1.py"
    "scripts\run_commander_briefing_evolution_v1.py"
    "scripts\send_telegram_minimal_ops_digest_v1.py"
    "scripts\Run-ACodeGovernorResearchBundle_v1.ps1"
    "scripts\Run-ACodeOperatorAssistLaneLightRoutine_v1.ps1"
    "scripts\build_a_code_light_ops_profile_v1.py"
)

$fail = $false
Write-Host "=== Commander Daily Prophecy Hero Loop readiness ===" -ForegroundColor Cyan

foreach ($rel in $scripts) {
    $p = Join-Path $WorkspaceRoot $rel
    if (Test-Path -LiteralPath $p) {
        Write-Host "[OK] $rel" -ForegroundColor Green
    } else {
        Write-Host "[MISS] $rel" -ForegroundColor Red
        $fail = $true
    }
}

foreach ($t in $tasks) {
    $tn = $t.Name
    $task = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if (-not $task) {
        if ($t.Required) {
            Write-Host "[MISS] Task $tn (required)" -ForegroundColor Red
            $fail = $true
        } else {
            Write-Host "[--] Optional task $tn" -ForegroundColor DarkYellow
        }
        continue
    }
    $i = Get-ScheduledTaskInfo -TaskName $tn
    Write-Host "[OK] $tn Next=$($i.NextRunTime) State=$($task.State)" -ForegroundColor Green
}

$sched = Join-Path $WorkspaceRoot "reports\commander_daily_prophecy_hero_loop_schedule_latest.json"
if (Test-Path -LiteralPath $sched) {
    Write-Host "[OK] $sched" -ForegroundColor Green
} else {
    Write-Host "[--] Schedule JSON not yet generated (run Register script)" -ForegroundColor DarkYellow
}

if ($fail) { exit 1 }
Write-Host "[OK] hero loop readiness" -ForegroundColor Green
exit 0
