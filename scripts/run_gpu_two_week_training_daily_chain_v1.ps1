param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$planPath = "docs/final/artifacts/gpu_two_week_training_plan_v1_latest.json"
if (-not (Test-Path -LiteralPath $planPath)) {
    throw "Training plan not found: $planPath"
}

$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$schedule = @($plan.schedule)
if ($schedule.Count -eq 0) {
    throw "Empty schedule in training plan."
}

$todayUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$entry = $schedule | Where-Object { $_.date_utc -eq $todayUtc } | Select-Object -First 1
if ($null -eq $entry) {
    $entry = $schedule[0]
}
$dayIndex = [int]$entry.day_index

Write-Host ("[daily-chain] day_index={0} date_utc={1} focus={2}" -f $dayIndex, $entry.date_utc, $entry.focus)
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts/run_gpu_two_week_training_day_v1.ps1" -DayIndex $dayIndex
py "scripts/build_gpu_two_week_training_dashboard_v1.py"

Write-Host "DONE: gpu two-week training daily chain complete."
