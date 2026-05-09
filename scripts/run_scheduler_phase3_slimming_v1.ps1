[CmdletBinding()]
param(
    [string]$PolicyPath = "docs/final/artifacts/scheduler_phase3_policy_v1.json",
    [switch]$ApplyChanges,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Parse-TimeToday {
    param([string]$Hm)
    $parts = $Hm.Split(":")
    if ($parts.Count -ne 2) {
        throw "Invalid HH:mm time: $Hm"
    }
    $h = [int]$parts[0]
    $m = [int]$parts[1]
    if ($h -lt 0 -or $h -gt 23 -or $m -lt 0 -or $m -gt 59) {
        throw "Time out of range: $Hm"
    }
    return ([datetime]::Today.AddHours($h).AddMinutes($m))
}

function Get-TaskInfoSafe {
    param([string]$TaskName)
    try {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
        return [pscustomobject]@{
            Exists = $true
            Task = $task
            Info = $info
        }
    } catch {
        return [pscustomobject]@{
            Exists = $false
            Task = $null
            Info = $null
        }
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not (Test-Path -LiteralPath $PolicyPath)) {
    throw "Policy file not found: $PolicyPath"
}

$policy = Get-Content -LiteralPath $PolicyPath -Raw | ConvertFrom-Json
$targetPrefix = [string]$policy.target_prefix
$startTime = Parse-TimeToday -Hm ([string]$policy.morning_window.start)
$endTime = Parse-TimeToday -Hm ([string]$policy.morning_window.end)

$disableTasks = @()
if ($policy.disable_tasks) {
    $disableTasks = @($policy.disable_tasks)
}

$rescheduleMap = @{}
if ($policy.reschedule_tasks) {
    foreach ($row in $policy.reschedule_tasks) {
        $rescheduleMap[[string]$row.task_name] = [string]$row.new_time
    }
}

$keepMorning = @{}
if ($policy.must_keep_morning_tasks) {
    foreach ($n in $policy.must_keep_morning_tasks) {
        $keepMorning[[string]$n] = $true
    }
}

$actions = New-Object System.Collections.Generic.List[object]

foreach ($name in $disableTasks) {
    $t = Get-TaskInfoSafe -TaskName $name
    if (-not $t.Exists) {
        $actions.Add([pscustomobject]@{
            task_name = $name
            action = "disable"
            status = "not_found"
            note = "Task not found"
        })
        continue
    }
    if ([string]$t.Task.State -eq "Disabled") {
        $actions.Add([pscustomobject]@{
            task_name = $name
            action = "disable"
            status = "skipped_already_disabled"
            note = ""
        })
        continue
    }

    if ($ApplyChanges -and -not $WhatIf) {
        Disable-ScheduledTask -TaskName $name | Out-Null
        $actions.Add([pscustomobject]@{
            task_name = $name
            action = "disable"
            status = "applied"
            note = ""
        })
    } else {
        $actions.Add([pscustomobject]@{
            task_name = $name
            action = "disable"
            status = "planned"
            note = ""
        })
    }
}

foreach ($kv in $rescheduleMap.GetEnumerator()) {
    $taskName = [string]$kv.Key
    $newTime = [string]$kv.Value
    $t = Get-TaskInfoSafe -TaskName $taskName
    if (-not $t.Exists) {
        $actions.Add([pscustomobject]@{
            task_name = $taskName
            action = "reschedule"
            status = "not_found"
            note = "Task not found"
            target_time = $newTime
        })
        continue
    }

    $trigger = New-ScheduledTaskTrigger -Daily -At (Parse-TimeToday -Hm $newTime)
    if ($ApplyChanges -and -not $WhatIf) {
        Set-ScheduledTask -TaskName $taskName -Trigger $trigger | Out-Null
        $actions.Add([pscustomobject]@{
            task_name = $taskName
            action = "reschedule"
            status = "applied"
            note = ""
            target_time = $newTime
        })
    } else {
        $actions.Add([pscustomobject]@{
            task_name = $taskName
            action = "reschedule"
            status = "planned"
            note = ""
            target_time = $newTime
        })
    }
}

$allEnabled = Get-ScheduledTask | Where-Object { $_.TaskName -like "*$targetPrefix*" -and $_.State -ne "Disabled" }
$windowRows = New-Object System.Collections.Generic.List[object]
foreach ($t in $allEnabled) {
    $i = Get-ScheduledTaskInfo -TaskName $t.TaskName -TaskPath $t.TaskPath
    if ($i.NextRunTime -ge $startTime -and $i.NextRunTime -lt $endTime) {
        $windowRows.Add([pscustomobject]@{
            task_name = $t.TaskName
            next_run = $i.NextRunTime.ToString("s")
            last_result = $i.LastTaskResult
            classification = $(if ($keepMorning.ContainsKey($t.TaskName)) { "keep_morning" } else { "candidate_reduce" })
        })
    }
}

$keepCount = ($windowRows | Where-Object { $_.classification -eq "keep_morning" } | Measure-Object).Count
$candidateCount = ($windowRows | Where-Object { $_.classification -eq "candidate_reduce" } | Measure-Object).Count

$sortedWindowRows = $windowRows | Sort-Object -Property @("next_run", "task_name")
$report = [ordered]@{
    schema = "scheduler_phase3_slimming_report_v1"
    generated_at = (Get-Date).ToString("s")
    apply_changes = [bool]$ApplyChanges
    what_if = [bool]$WhatIf
    policy_path = $PolicyPath
    summary = [ordered]@{
        enabled_target_tasks = $allEnabled.Count
        morning_window_task_count = $windowRows.Count
        keep_morning_count = $keepCount
        candidate_reduce_count = $candidateCount
    }
    actions = $actions.ToArray()
    morning_window_tasks = @($sortedWindowRows)
}

$outDir = Join-Path $repoRoot "reports"
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
$outJson = Join-Path $outDir "scheduler_phase3_slimming_latest.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $outJson

Write-Host ("[scheduler-phase3] apply_changes={0} what_if={1}" -f [bool]$ApplyChanges, [bool]$WhatIf)
Write-Host ("[scheduler-phase3] enabled_target_tasks={0} morning_window={1} keep={2} candidate_reduce={3}" -f $report.summary.enabled_target_tasks, $report.summary.morning_window_task_count, $report.summary.keep_morning_count, $report.summary.candidate_reduce_count)
Write-Host ("[scheduler-phase3] report={0}" -f $outJson)
