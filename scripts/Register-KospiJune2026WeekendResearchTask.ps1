#Requires -Version 5.1
<#
.SYNOPSIS
  Register weekly Saturday task for June 2026 KOSPI weekend B-track research [HYPO].

.EXAMPLE
  pwsh -File scripts/Register-KospiJune2026WeekendResearchTask.ps1
  pwsh -File scripts/Register-KospiJune2026WeekendResearchTask.ps1 -Remove
  pwsh -File scripts/Register-KospiJune2026WeekendResearchTask.ps1 -DryRun
#>
param(
    [string]$TaskName = "MKM_Kospi_June2026_Weekend_Research",
    [string]$WeeklyAt = "10:00",
    [ValidateSet("Saturday", "Sunday")]
    [string]$DayOfWeek = "Saturday",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$YearMonth = "2026-06",
    [switch]$Remove,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$bundle = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026WeekendResearchBundle_v1.ps1"

if ($Remove) {
    if ($DryRun) {
        Write-Host "[dry-run] Unregister-ScheduledTask $TaskName"
        exit 0
    }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $bundle)) {
    throw "Missing bundle script: $bundle"
}

$parts = $WeeklyAt -split ':'
if ($parts.Count -lt 2) { throw "WeeklyAt must be HH:mm, got: $WeeklyAt" }
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0

$argList = @(
    "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", $bundle,
    "-WorkspaceRoot", $WorkspaceRoot,
    "-YearMonth", $YearMonth
)
$argLine = ($argList | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join ' '

if ($DryRun) {
    Write-Host "[dry-run] Register $TaskName $DayOfWeek at $WeeklyAt -> $argLine"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $DayOfWeek -At $atToday
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 120) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "June KOSPI weekend B-track research bundle [HYPO research_only]" -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered: $TaskName $DayOfWeek at $WeeklyAt Next=$($info.NextRunTime)"

$sched = [ordered]@{
    schema           = "kospi_june2026_weekend_research_schedule_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    hypothesis_tier  = "B"
    research_only    = $true
    track_wall       = "no_track_a_live_auto_merge"
    task_name        = $TaskName
    day_of_week      = $DayOfWeek
    at_kst           = $WeeklyAt
    year_month       = $YearMonth
    bundle_script    = "scripts/Invoke-KospiJune2026WeekendResearchBundle_v1.ps1"
    verify           = "pwsh -File scripts/Verify-KospiJune2026WeekendResearchTask.ps1"
    manual           = "pwsh -File scripts/Invoke-KospiJune2026WeekendResearchBundle_v1.ps1"
}
$outJson = Join-Path $WorkspaceRoot "reports\kospi_june2026_weekend_research_schedule_latest.json"
$sched | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outJson -Encoding utf8
Write-Host "Wrote $outJson"
Write-Host "Verify: pwsh -File scripts/Verify-KospiJune2026WeekendResearchTask.ps1" -ForegroundColor DarkGray
