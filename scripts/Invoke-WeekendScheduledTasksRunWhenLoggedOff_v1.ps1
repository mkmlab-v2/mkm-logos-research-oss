#Requires -Version 5.1
<#
.SYNOPSIS
  Re-register Sunday MS v2 shadow + Oracle recommended-eval tasks for logged-off run.

.DESCRIPTION
  Must run elevated (Administrator). Uses repo SSOT register scripts only — no C:\MKM paths.

.EXAMPLE
  # Right-click PowerShell -> Run as administrator:
  Set-Location C:\workspace
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-WeekendScheduledTasksRunWhenLoggedOff_v1.ps1

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-WeekendScheduledTasksRunWhenLoggedOff_v1.ps1 -TestRunV2Wire
#>
param(
    [switch]$TestRunV2Wire,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$isAdmin = ([Security.Principal.WindowsPrincipal] (
    [Security.Principal.WindowsIdentity]::GetCurrent()
)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[FAIL] Run from elevated PowerShell (Run as administrator)." -ForegroundColor Red
    Write-Host "  cd $WorkspaceRoot"
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Invoke-WeekendScheduledTasksRunWhenLoggedOff_v1.ps1"
    exit 2
}

$log = Join-Path $WorkspaceRoot "reports\weekend_scheduled_tasks_runwhenloggedoff_v1_latest.json"
$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step($name, $exitCode, $note) {
    $steps.Add([ordered]@{
        name     = $name
        exit_code = $exitCode
        note     = $note
    }) | Out-Null
}

Write-Host "[OK] Elevated. Registering weekend tasks with -RunWhenLoggedOff ..." -ForegroundColor Green

& (Join-Path $WorkspaceRoot "scripts\Register-V2WireShadowMeteringWeeklyTask.ps1") -RunWhenLoggedOff
Add-Step "register_v2_wire" $LASTEXITCODE "S4U principal; Sunday 10:15"

& (Join-Path $WorkspaceRoot "scripts\Register-BtrackRecommendedEvalAutoSweepWeeklyTask.ps1") -RunWhenLoggedOff
Add-Step "register_oracle_sweep" $LASTEXITCODE "S4U principal; Sunday 09:45"

& (Join-Path $WorkspaceRoot "scripts\Register-CompressionWeeklyGovernanceTask.ps1") -RunWhenLoggedOff
Add-Step "register_compression_weekly" $LASTEXITCODE "S4U principal; Sunday 07:00"

& (Join-Path $WorkspaceRoot "scripts\Register-SundayAutomationAuditTask_v1.ps1") -RunWhenLoggedOff
Add-Step "register_sunday_audit" $LASTEXITCODE "S4U principal; Sunday 10:30 post-flight audit"

$taskNames = @(
    "MKM_Compression_WeeklyGovernance",
    "MKM-V2-Wire-Shadow-Metering-Weekly",
    "MKM-BTrack-RecommendedEval-AutoSweep-Weekly",
    "MKM-Sunday-Automation-LastResult-Audit"
)
$queries = @()
foreach ($tn in $taskNames) {
    $info = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if ($info) {
        $ti = Get-ScheduledTaskInfo -TaskName $tn
        $queries += [ordered]@{
            task_name      = $tn
            state          = $info.State.ToString()
            logon_type     = $info.Principal.LogonType.ToString()
            run_as         = $info.Principal.UserId
            next_run       = $ti.NextRunTime.ToString()
            last_result    = $ti.LastTaskResult
        }
    }
}

if ($TestRunV2Wire) {
    Write-Host "[RUN] Test fire: MKM-V2-Wire-Shadow-Metering-Weekly" -ForegroundColor Cyan
    schtasks /Run /TN "MKM-V2-Wire-Shadow-Metering-Weekly" | Out-Host
    $deadline = (Get-Date).AddMinutes(5)
    $last = -1
    do {
        Start-Sleep -Seconds 5
        $ti = Get-ScheduledTaskInfo -TaskName "MKM-V2-Wire-Shadow-Metering-Weekly"
        $last = [int]$ti.LastTaskResult
    } while ((Get-Date) -lt $deadline -and $last -eq 267011)
    Add-Step "test_run_v2_wire" $last "LastTaskResult after /Run (0=success; 267011=still running)"
}

$payload = [ordered]@{
    schema           = "weekend_scheduled_tasks_runwhenloggedoff_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    workspace_root   = $WorkspaceRoot
    steps            = $steps
    tasks            = $queries
}
$dir = Split-Path -Parent $log
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $log -Encoding UTF8
Write-Host "WROTE: $log" -ForegroundColor Green

$bad = $steps | Where-Object { $_.exit_code -ne 0 }
if ($bad) { exit 1 }
exit 0
