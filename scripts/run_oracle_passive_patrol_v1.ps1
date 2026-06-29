#Requires -Version 5.1
<#
.SYNOPSIS
  Oracle passive patrol: scheduled-task matrix + readiness + shadow log summary (non-gating).

.DESCRIPTION
  B-track / research_only. Does not trigger live routing or SEND.
  Writes reports/oracle_passive_patrol_v1_latest.json

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_oracle_passive_patrol_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$OutJson = "",
    [switch]$SkipSundayAudit
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\oracle_passive_patrol_v1_latest.json"
}

$patrolTasks = @(
    "MKM-BTrack-DailyHypothesis-Chain",
    "MKM-Prophecy-Daily-Eval-Report",
    "MKM-Prophecy-Panel-24h-Alerts",
    "MKM-Telegram-Minimal-Daily-Digest",
    "MKM-Commander-Evening-Briefing-Score",
    "MKM-BTrack-RecommendedEval-AutoSweep-Weekly",
    "MKM-Sunday-Automation-LastResult-Audit"
)

$steps = [ordered]@{}
$taskMatrix = @()

foreach ($taskName in $patrolTasks) {
    $row = [ordered]@{
        task_name   = $taskName
        exists      = $false
        state       = $null
        last_result = $null
        last_run    = $null
        next_run    = $null
    }
    $t = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($t) {
        $i = Get-ScheduledTaskInfo -TaskName $taskName
        $row.exists = $true
        $row.state = [string]$t.State
        $row.last_result = [int64][uint32]$i.LastTaskResult
        if ($i.LastRunTime -and $i.LastRunTime -ne [datetime]::MinValue) {
            $row.last_run = $i.LastRunTime.ToString("yyyy-MM-dd HH:mm:ss")
        }
        if ($i.NextRunTime -and $i.NextRunTime -ne [datetime]::MinValue) {
            $row.next_run = $i.NextRunTime.ToString("yyyy-MM-dd HH:mm:ss")
        }
    }
    $taskMatrix += $row
}

$readinessExit = 0
$readinessScript = Join-Path $WorkspaceRoot "scripts\Verify-BtrackProphecyDailyOpsReadiness_v1.ps1"
if (Test-Path -LiteralPath $readinessScript) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $readinessScript -WorkspaceRoot $WorkspaceRoot
    $readinessExit = [int]$LASTEXITCODE
} else {
    Write-Warning "Missing readiness script: $readinessScript"
    $readinessExit = 1
}
$steps.readiness_exit = $readinessExit

$shadowExit = 0
$shadowScript = Join-Path $WorkspaceRoot "scripts\summarize_btrack_31k41k_prophecy_shadow_log_v1.py"
if (Test-Path -LiteralPath $shadowScript) {
    & py $shadowScript
    $shadowExit = [int]$LASTEXITCODE
} else {
    Write-Warning "Missing shadow summary script: $shadowScript"
    $shadowExit = 1
}
$steps.shadow_summary_exit = $shadowExit

$sundayExit = 0
if (-not $SkipSundayAudit) {
    $sundayScript = Join-Path $WorkspaceRoot "scripts\Invoke-CheckSundayAutomationLastResult_v1.ps1"
    if (Test-Path -LiteralPath $sundayScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $sundayScript -WorkspaceRoot $WorkspaceRoot -AllowStaleLastRun
        $sundayExit = [int]$LASTEXITCODE
    } else {
        Write-Warning "Missing Sunday audit script: $sundayScript"
        $sundayExit = 1
    }
} else {
    $sundayExit = 0
}
$steps.sunday_audit_exit = $sundayExit

$shadowGateDecision = "UNKNOWN"
$gateScript = Join-Path $WorkspaceRoot "scripts\check_btrack_31k41k_prophecy_shadow_gate_v1.py"
if (Test-Path -LiteralPath $gateScript) {
    & py $gateScript --gate-mode allowlist_review
    $gateExit = [int]$LASTEXITCODE
    $gateOut = Join-Path $WorkspaceRoot "docs\final\artifacts\btrack_31k41k_prophecy_shadow_gate_v1_latest.json"
    if (Test-Path -LiteralPath $gateOut) {
        try {
            $g = Get-Content -LiteralPath $gateOut -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($g.decision) { $shadowGateDecision = [string]$g.decision }
        } catch {
            $shadowGateDecision = "PARSE_ERROR"
        }
    }
    $steps.shadow_gate_exit = $gateExit
} else {
    $steps.shadow_gate_exit = 1
}

$nonZeroResults = @($taskMatrix | Where-Object { $_.exists -and ($null -ne $_.last_result) -and ([int64]$_.last_result -ne 0) })
$tasksLastResultAllZero = ($nonZeroResults.Count -eq 0)

# Non-gating patrol: readiness + shadow summary must pass; task/sunday issues are advisory.
$patrolOk = ($readinessExit -eq 0) -and ($shadowExit -eq 0)

$doc = [ordered]@{
    schema                 = "oracle_passive_patrol_v1"
    generated_at_utc       = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    research_only          = $true
    non_gating             = $true
    send_gate              = "HOLD"
    bounded_program_outcome = "CONTINUE_BOUNDED"
    task_matrix            = $taskMatrix
    tasks_last_result_all_zero = $tasksLastResultAllZero
    shadow_gate_decision   = $shadowGateDecision
    steps                  = $steps
    patrol_ok              = $patrolOk
}

$dir = Split-Path -Parent $OutJson
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$doc | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $OutJson -Encoding utf8

Write-Host "WROTE: $OutJson patrol_ok=$patrolOk shadow_gate=$shadowGateDecision" -ForegroundColor Cyan
if (-not $patrolOk) { exit 1 }
exit 0
