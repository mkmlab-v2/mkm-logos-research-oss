#Requires -Version 5.1
<#
.SYNOPSIS
  Print (and optionally validate) the scheduled task for Track A commercialization daily chain.

.DESCRIPTION
  Fact-Lock spot check after Register-TrackACommercializationDailyTask.ps1.
  Use -Strict to assert working directory, chain script in arguments, and -GateMode value.
  Use -AllowMissing to exit 0 when the task is not registered (e.g. fresh clone before register).
#>
[CmdletBinding()]
param(
    [string]$TaskName = "MKM_TrackA_CommercializationDaily",
    [string]$WorkspaceRoot = "",
    [ValidateSet("warning", "block")]
    [string]$ExpectedGateMode = "warning",
    [switch]$Strict,
    [switch]$AllowMissing
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Split-Path -Parent $PSScriptRoot)
}
$WorkspaceRoot = [System.IO.Path]::GetFullPath($WorkspaceRoot.Trim())

$t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $t) {
    if ($AllowMissing) {
        Write-Output "task_name=$TaskName"
        Write-Output "task_present=false"
        Write-Output "allow_missing=true"
        exit 0
    }
    throw "Scheduled task not found: $TaskName (register with Register-TrackACommercializationDailyTask.ps1 or pass -AllowMissing)"
}

$info = Get-ScheduledTaskInfo -InputObject $t
$a = $t.Actions[0]

Write-Output "task_name=$TaskName"
Write-Output ("task_present=true")
Write-Output ("state={0}" -f $t.State)
Write-Output ("last_run_time={0}" -f $info.LastRunTime)
Write-Output ("last_task_result={0}" -f $info.LastTaskResult)
Write-Output ("execute={0}" -f $a.Execute)
Write-Output ("arguments={0}" -f $a.Arguments)
Write-Output ("working_directory={0}" -f $a.WorkingDirectory)

if ($Strict) {
    $ex = [string]$a.Execute
    if ([System.IO.Path]::GetFileName($ex) -ine 'powershell.exe') {
        throw "Strict: expected powershell.exe execute, got: $ex"
    }
    $arg = [string]$a.Arguments
    if ($arg -notmatch 'run_track_a_commercialization_daily_chain\.ps1') {
        throw "Strict: arguments must reference run_track_a_commercialization_daily_chain.ps1"
    }
    $gatePat = '-GateMode\s+' + [regex]::Escape($ExpectedGateMode)
    if ($arg -notmatch $gatePat) {
        throw "Strict: arguments must contain -GateMode $ExpectedGateMode (got: $arg)"
    }
    $wdRaw = [string]$a.WorkingDirectory
    if ([string]::IsNullOrWhiteSpace($wdRaw)) {
        throw "Strict: working_directory is empty"
    }
    $wdNorm = [System.IO.Path]::GetFullPath($wdRaw.Trim())
    if ($wdNorm -cne $WorkspaceRoot) {
        throw "Strict: working_directory mismatch expected=$WorkspaceRoot actual=$wdNorm"
    }
}
