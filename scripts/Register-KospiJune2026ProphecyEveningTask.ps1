#Requires -Version 5.1

<#

.SYNOPSIS

  Register weekday morning + evening tasks for June 2026 KOSPI prophecy [HYPO].



.DESCRIPTION

  B-track research_only · recommended path: evening accumulates June forward (SkipHeavyResearch).

  Morning rebuilds calendar + 4AI report before session.



.EXAMPLE

  pwsh -File scripts/Register-KospiJune2026ProphecyEveningTask.ps1

  pwsh -File scripts/Register-KospiJune2026ProphecyEveningTask.ps1 -Remove

  pwsh -File scripts/Register-KospiJune2026ProphecyEveningTask.ps1 -EveningOnly

#>

param(

    [string]$EveningTaskName = "MKM_Kospi_June2026_Prophecy_Evening",

    [string]$MorningTaskName = "MKM_Kospi_June2026_Prophecy_Morning",

    [string]$EveningAt = "18:35",

    [string]$MorningAt = "08:05",

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$YearMonth = "2026-06",

    [switch]$Remove,

    [switch]$EveningOnly,

    [switch]$DryRun

)



$ErrorActionPreference = "Stop"

$loop = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026ProphecyLoop_v1.ps1"



function Remove-KospiJuneTask([string]$Name) {
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



function Register-KospiJuneTask {

    param(

        [string]$Name,

        [string]$At,

        [string]$Phase,

        [string[]]$ExtraArgs = @()

    )

    $argList = @(

        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $loop,

        "-WorkspaceRoot", $WorkspaceRoot,

        "-Phase", $Phase,

        "-YearMonth", $YearMonth

    ) + $ExtraArgs

    $argLine = ($argList | ForEach-Object {

        if ($_ -match '\s') { "`"$_`"" } else { $_ }

    }) -join ' '



    if ($DryRun) {

        Write-Host "[dry-run] Register $Name WEEKLY Mon-Fri at $At -> $argLine"

        return

    }



    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argLine -WorkingDirectory $WorkspaceRoot

    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At $At

    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew

    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "June KOSPI prophecy $Phase [HYPO research_only]" -Force | Out-Null

    $info = Get-ScheduledTaskInfo -TaskName $Name

    Write-Host "Registered: $Name Mon-Fri at $At Next=$($info.NextRunTime)"

}



if ($Remove) {

    Remove-KospiJuneTask $EveningTaskName

    if (-not $EveningOnly) { Remove-KospiJuneTask $MorningTaskName }

    exit 0

}



if (-not (Test-Path -LiteralPath $loop)) {

    throw "Missing loop script: $loop"

}



Register-KospiJuneTask -Name $EveningTaskName -At $EveningAt -Phase Evening -ExtraArgs @("-SkipHeavyResearch")



if (-not $EveningOnly) {

    Register-KospiJuneTask -Name $MorningTaskName -At $MorningAt -Phase Morning

}



if (-not $DryRun) {

    $sched = [ordered]@{

        schema           = "kospi_june2026_prophecy_daily_schedule_v1"

        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")

        hypothesis_tier  = "B"

        research_only    = $true

        track_wall       = "no_track_a_live_auto_merge"

        year_month       = $YearMonth

        weekday_only     = $true

        tasks            = @(

            @{ name = $MorningTaskName; at_kst = $MorningAt; phase = "Morning"; skip_heavy_research = $false }

            @{ name = $EveningTaskName; at_kst = $EveningAt; phase = "Evening"; skip_heavy_research = $true }

        )

        verify           = "pwsh -File scripts/Verify-KospiJune2026ProphecyEveningTask.ps1"

        manual_evening   = "pwsh -File scripts/Invoke-KospiJune2026ProphecyLoop_v1.ps1 -Phase Evening -YearMonth $YearMonth -SkipHeavyResearch"

    }

    $outJson = Join-Path $WorkspaceRoot "reports\kospi_june2026_prophecy_daily_schedule_latest.json"

    $sched | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $outJson -Encoding utf8

    Write-Host "Wrote $outJson"

}



Write-Host "Verify: pwsh -File scripts/Verify-KospiJune2026ProphecyEveningTask.ps1" -ForegroundColor DarkGray

