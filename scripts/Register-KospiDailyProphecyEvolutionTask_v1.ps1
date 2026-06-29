#Requires -Version 5.1

<#
.SYNOPSIS
  Register weekday morning/evening + Saturday weekend tasks for KOSPI daily prophecy evolution [HYPO].

.DESCRIPTION
  B-track research_only · dual_path_v2_router shadow · send_gate HOLD.
  Replaces June-only Invoke-KospiJune2026ProphecyLoop for rolling year-month OOS.

.EXAMPLE
  pwsh -File scripts/Register-KospiDailyProphecyEvolutionTask_v1.ps1
  pwsh -File scripts/Register-KospiDailyProphecyEvolutionTask_v1.ps1 -YearMonth 2026-07
  pwsh -File scripts/Register-KospiDailyProphecyEvolutionTask_v1.ps1 -Remove
#>

param(
    [string]$MorningTaskName = "MKM_Kospi_Daily_Prophecy_Evolution_Morning_v1",
    [string]$EveningTaskName = "MKM_Kospi_Daily_Prophecy_Evolution_Evening_v1",
    [string]$WeekendTaskName = "MKM_Kospi_Daily_Prophecy_Evolution_Weekend_v1",
    [string]$SundayPremarketTaskName = "MKM_Kospi_Daily_Premarket_Ingest_Sunday_v1",
    [string]$MorningAt = "08:05",
    [string]$EveningAt = "18:35",
    [string]$WeekendAt = "10:00",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$YearMonth = (Get-Date).ToString("yyyy-MM"),
    [switch]$Remove,
    [switch]$EveningOnly,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$loop = Join-Path $WorkspaceRoot "scripts\run_kospi_daily_prophecy_evolution_loop_v1.py"

function Remove-KospiEvolutionTask([string]$Name) {
    if ($DryRun) {
        Write-Host "[dry-run] Unregister-ScheduledTask $Name"
        return
    }
    $existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false | Out-Null
        Write-Host "Removed task: $Name"
    }
}

function Register-KospiEvolutionTask {
    param(
        [string]$Name,
        [string]$At,
        [string]$Phase,
        [ValidateSet("Weekdays", "Saturday", "Sunday")]
        [string]$Schedule = "Weekdays",
        [string[]]$ExtraArgs = @()
    )

    $argList = @(
        "scripts/run_kospi_daily_prophecy_evolution_loop_v1.py",
        "--phase", $Phase,
        "--year-month", $YearMonth
    ) + $ExtraArgs

    $argLine = ($argList | ForEach-Object {
        if ($_ -match '\s') { "`"$_`"" } else { $_ }
    }) -join ' '

    if ($DryRun) {
        $days = if ($Schedule -eq "Saturday") { "Saturday" } else { "Mon-Fri" }
        Write-Host "[dry-run] Register $Name $days at $At -> py $argLine"
        return
    }

    $action = New-ScheduledTaskAction -Execute "py" -Argument $argLine -WorkingDirectory $WorkspaceRoot
    if ($Schedule -eq "Saturday") {
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $At
    } elseif ($Schedule -eq "Sunday") {
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $At
    } else {
        $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $At
    }
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "KOSPI daily prophecy evolution $Phase [HYPO research_only]" -Force | Out-Null
    $info = Get-ScheduledTaskInfo -TaskName $Name
    Write-Host "Registered: $Name at $At Next=$($info.NextRunTime)"
}

if ($Remove) {
    Remove-KospiEvolutionTask $EveningTaskName
    if (-not $EveningOnly) {
        Remove-KospiEvolutionTask $MorningTaskName
        Remove-KospiEvolutionTask $WeekendTaskName
        Remove-KospiEvolutionTask $SundayPremarketTaskName
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $loop)) {
    throw "Missing loop script: $loop"
}

Register-KospiEvolutionTask -Name $EveningTaskName -At $EveningAt -Phase evening -ExtraArgs @("--skip-heavy")

if (-not $EveningOnly) {
    Register-KospiEvolutionTask -Name $MorningTaskName -At $MorningAt -Phase morning
    Register-KospiEvolutionTask -Name $WeekendTaskName -At $WeekendAt -Phase weekend -Schedule Saturday
    if (-not $DryRun) {
        $sunAction = New-ScheduledTaskAction -Execute "py" -Argument "scripts/run_kospi_premarket_news_overnight_ingest_chain_v1.py --allow-naver-cache-fallback" -WorkingDirectory $WorkspaceRoot
        $sunTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $WeekendAt
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew
        $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
        Register-ScheduledTask -TaskName $SundayPremarketTaskName -Action $sunAction -Trigger $sunTrigger -Settings $settings -Principal $principal -Description "KOSPI Sunday premarket ingest [HYPO]" -Force | Out-Null
        $info = Get-ScheduledTaskInfo -TaskName $SundayPremarketTaskName
        Write-Host "Registered: $SundayPremarketTaskName Sunday at $WeekendAt Next=$($info.NextRunTime)"
    } else {
        Write-Host "[dry-run] Register $SundayPremarketTaskName Sunday at $WeekendAt -> premarket ingest only"
    }
}

if (-not $DryRun) {
    $sched = [ordered]@{
        schema           = "kospi_daily_prophecy_evolution_schedule_v1"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        hypothesis_tier  = "B"
        research_only    = $true
        send_gate        = "HOLD"
        track_wall       = "no_track_a_live_auto_merge"
        year_month       = $YearMonth
        hook             = "scripts/run_kospi_daily_prophecy_evolution_loop_v1.py"
        tasks            = @(
            @{ name = $MorningTaskName; at_kst = $MorningAt; phase = "morning"; days = "Mon-Fri" }
            @{ name = $EveningTaskName; at_kst = $EveningAt; phase = "evening"; days = "Mon-Fri"; skip_heavy = $true }
            @{ name = $WeekendTaskName; at_kst = $WeekendAt; phase = "weekend"; days = "Saturday" }
            @{ name = $SundayPremarketTaskName; at_kst = $WeekendAt; phase = "premarket_ingest"; days = "Sunday" }
        )
        verify           = "pwsh -File scripts/Verify-KospiDailyProphecyEvolutionTask_v1.ps1"
        manual_evening   = "py scripts/run_kospi_daily_prophecy_evolution_loop_v1.py --phase evening --year-month $YearMonth --skip-heavy"
    }
    $outJson = Join-Path $WorkspaceRoot "reports\kospi_daily_prophecy_evolution_schedule_v1_latest.json"
    $sched | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outJson -Encoding utf8
    Write-Host "Wrote $outJson"
}

Write-Host "Verify: pwsh -File scripts/Verify-KospiDailyProphecyEvolutionTask_v1.ps1 -YearMonth $YearMonth" -ForegroundColor DarkGray
