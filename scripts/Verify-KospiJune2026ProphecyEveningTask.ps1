<#

.SYNOPSIS

  Spot-check MKM KOSPI June 2026 morning + evening scheduled tasks [HYPO].



.EXAMPLE

  pwsh -File scripts/Verify-KospiJune2026ProphecyEveningTask.ps1

#>

[CmdletBinding()]

param(

    [string]$EveningTaskName = "MKM_Kospi_June2026_Prophecy_Evening",

    [string]$MorningTaskName = "MKM_Kospi_June2026_Prophecy_Morning",

    [string]$WorkspaceRoot = "C:\workspace",

    [switch]$EveningOnly

)



Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"



$expectedLoop = Join-Path $WorkspaceRoot "scripts\Invoke-KospiJune2026ProphecyLoop_v1.ps1"

$fail = $false



function Test-KospiJuneTask {

    param(

        [string]$TaskName,

        [string]$ExpectedPhase,

        [bool]$RequireSkipHeavy,

        [bool]$Required = $true

    )

    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if (-not $t) {

        if ($Required) {

            Write-Output "${TaskName}_present=false"

            $script:fail = $true

        } else {

            Write-Output "${TaskName}_present=optional_missing"

        }

        return

    }

    $info = Get-ScheduledTaskInfo -InputObject $t

    $a = $t.Actions[0]

    $args = [string]$a.Arguments



    $loopOk = ($args -match "Invoke-KospiJune2026ProphecyLoop_v1\.ps1")

    $phaseOk = ($args -match "-Phase\s+$ExpectedPhase")

    $yearOk = ($args -match "-YearMonth\s+2026-06")

    $skipOk = if ($RequireSkipHeavy) { ($args -match "-SkipHeavyResearch") } else { $true }



    Write-Output "task_name=$TaskName"

    Write-Output ("state={0}" -f $t.State)

    Write-Output ("next_run_time={0}" -f $info.NextRunTime)

    Write-Output ("last_run_time={0}" -f $info.LastRunTime)

    Write-Output ("last_task_result={0}" -f $info.LastTaskResult)

    Write-Output ("phase_{0}_ok={1}" -f $ExpectedPhase.ToLower(), $phaseOk)

    Write-Output ("skip_heavy_research_ok={0}" -f $skipOk)

    Write-Output ("year_month_2026_06_ok={0}" -f $yearOk)

    Write-Output ("evening_loop_action_ok={0}" -f $loopOk)



    if (-not ($loopOk -and $phaseOk -and $yearOk -and $skipOk)) {

        $script:fail = $true

    }

}



if (-not (Test-Path -LiteralPath $expectedLoop)) {

    Write-Error "Missing loop script: $expectedLoop"

    exit 2

}



Test-KospiJuneTask -TaskName $EveningTaskName -ExpectedPhase Evening -RequireSkipHeavy $true -Required $true

if (-not $EveningOnly) {

    Test-KospiJuneTask -TaskName $MorningTaskName -ExpectedPhase Morning -RequireSkipHeavy $false -Required $true

}



$sched = Join-Path $WorkspaceRoot "reports\kospi_june2026_prophecy_daily_schedule_latest.json"

if (Test-Path -LiteralPath $sched) {

    Write-Output "schedule_json_ok=true"

} else {

    Write-Output "schedule_json_ok=false"

    $fail = $true

}



if ($fail) { exit 1 }

exit 0

