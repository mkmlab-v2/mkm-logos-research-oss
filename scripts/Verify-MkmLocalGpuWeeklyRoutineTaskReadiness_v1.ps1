#Requires -Version 5.1
<#
.SYNOPSIS
  Verify MKM_Local_Gpu_Weekly_Routine scheduled task wiring.
#>
param(
    [string]$TaskName = "MKM_Local_Gpu_Weekly_Routine"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $root "scripts\Run-LocalGpuWeeklyRoutine_v1.ps1"
$report = Join-Path $root "reports\local_gpu_weekly_routine_readiness_v1_latest.json"

$taskOk = $false
$state = "missing"
$lastResult = $null
$hasRunner = $false
$hasAudioFlag = $false
$hasMediaBakeFlag = $false

try {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $info = Get-ScheduledTaskInfo -InputObject $t
    $state = [string]$t.State
    $lastResult = $info.LastTaskResult
    $argStr = [string]$t.Actions[0].Arguments
    $hasRunner = $argStr -match 'Run-LocalGpuWeeklyRoutine_v1\.ps1'
    $hasAudioFlag = $argStr -match 'IncludeAudioGenerate'
    $hasMediaBakeFlag = $argStr -match 'IncludeMediaThinSliceBake'
    $taskOk = $hasRunner
}
catch {
    $taskOk = $false
}

$doc = [ordered]@{
    schema                         = "local_gpu_weekly_routine_readiness_v1"
    checked_at_utc                 = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    task_name                      = $TaskName
    task_registered                = $taskOk
    task_state                     = $state
    last_task_result               = $lastResult
    runner_path                    = $runner
    runner_exists                  = (Test-Path -LiteralPath $runner)
    include_audio_generate_in_task = $hasAudioFlag
    include_media_thin_slice_bake_in_task = $hasMediaBakeFlag
    register_script                = "scripts/Register-MkmLocalGpuWeeklyRoutineTask.ps1"
    recommended_register           = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-MkmLocalGpuWeeklyRoutineTask.ps1 -IncludeAudioGenerate -IncludeMediaThinSliceBake"
    ok                             = ($taskOk -and (Test-Path -LiteralPath $runner))
}

($doc | ConvertTo-Json -Depth 4) + "`n" | Set-Content -LiteralPath $report -Encoding utf8
Write-Output ($doc | ConvertTo-Json -Compress)
exit $(if ($doc.ok) { 0 } else { 1 })
