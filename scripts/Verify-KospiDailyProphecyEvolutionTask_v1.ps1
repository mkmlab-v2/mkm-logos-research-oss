<#
.SYNOPSIS
  Spot-check MKM KOSPI daily prophecy evolution scheduled tasks [HYPO].

.EXAMPLE
  pwsh -File scripts/Verify-KospiDailyProphecyEvolutionTask_v1.ps1
  pwsh -File scripts/Verify-KospiDailyProphecyEvolutionTask_v1.ps1 -YearMonth 2026-07
#>

[CmdletBinding()]
param(
    [string]$MorningTaskName = "MKM_Kospi_Daily_Prophecy_Evolution_Morning_v1",
    [string]$EveningTaskName = "MKM_Kospi_Daily_Prophecy_Evolution_Evening_v1",
    [string]$WeekendTaskName = "MKM_Kospi_Daily_Prophecy_Evolution_Weekend_v1",
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$YearMonth = (Get-Date).ToString("yyyy-MM"),
    [switch]$EveningOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$expectedLoop = Join-Path $WorkspaceRoot "scripts\run_kospi_daily_prophecy_evolution_loop_v1.py"
$fail = $false

function Test-KospiEvolutionTask {
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
    $exeOk = ([string]$a.Execute -match '^(py|py\.exe)$')
    $loopOk = ($args -match "run_kospi_daily_prophecy_evolution_loop_v1\.py")
    $phaseOk = ($args -match "--phase\s+$ExpectedPhase")
    $yearOk = ($args -match "--year-month\s+$([regex]::Escape($YearMonth))")
    $skipOk = if ($RequireSkipHeavy) { ($args -match "--skip-heavy") } else { $true }

    Write-Output "task_name=$TaskName"
    Write-Output ("state={0}" -f $t.State)
    Write-Output ("next_run_time={0}" -f $info.NextRunTime)
    Write-Output ("last_run_time={0}" -f $info.LastRunTime)
    Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
    Write-Output ("phase_{0}_ok={1}" -f $ExpectedPhase, $phaseOk)
    Write-Output ("skip_heavy_ok={0}" -f $skipOk)
    Write-Output ("year_month_{0}_ok={1}" -f ($YearMonth -replace '-', '_'), $yearOk)
    Write-Output ("evolution_loop_action_ok={0}" -f ($exeOk -and $loopOk))

    if (-not ($exeOk -and $loopOk -and $phaseOk -and $yearOk -and $skipOk)) {
        $script:fail = $true
    }
}

if (-not (Test-Path -LiteralPath $expectedLoop)) {
    Write-Error "Missing loop script: $expectedLoop"
    exit 2
}

Test-KospiEvolutionTask -TaskName $EveningTaskName -ExpectedPhase evening -RequireSkipHeavy $true -Required $true
if (-not $EveningOnly) {
    Test-KospiEvolutionTask -TaskName $MorningTaskName -ExpectedPhase morning -RequireSkipHeavy $false -Required $true
    Test-KospiEvolutionTask -TaskName $WeekendTaskName -ExpectedPhase weekend -RequireSkipHeavy $false -Required $true
}

$sched = Join-Path $WorkspaceRoot "reports\kospi_daily_prophecy_evolution_schedule_v1_latest.json"
if (Test-Path -LiteralPath $sched) {
    Write-Output "schedule_json_ok=true"
} else {
    Write-Output "schedule_json_ok=false"
    $fail = $true
}

if ($fail) { exit 1 }
exit 0
