#Requires -Version 5.1
<#
.SYNOPSIS
  Verify A-code operator-assist lane scripts, artifacts, and optional weekly task (RQ-031).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TaskName = "MKM-ACode-OperatorAssistLane-Weekly",
    [string]$LightTaskName = "MKM-ACode-OperatorAssistLane-Weekly-Light",
    [switch]$RequireScheduledTask,
    [switch]$RequireBothWeeklyTasks
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$scripts = @(
    "scripts\Run-ACodeOperatorAssistLaneRoutine_v1.ps1"
    "scripts\Run-ACodePromotionRqDiscussionBundle_v1.ps1"
    "scripts\build_a_code_operator_assist_lane_v1.py"
    "scripts\check_a_code_operator_assist_lane_gate_v1.py"
    "scripts\build_a_code_constitution_pointer_pr_draft_v1.py"
    "scripts\check_a_code_constitution_pointer_row_v1.py"
    "scripts\check_a_code_rq_close_gate_v1.py"
    "scripts\build_a_code_light_ops_profile_v1.py"
    "scripts\Run-ACodeOperatorAssistLaneLightRoutine_v1.ps1"
    "scripts\build_a_code_rq_close_human_checklist_v1.py"
    "scripts\Run-ACodeRqCloseHumanChecklistBundle_v1.ps1"
    "scripts\record_a_code_rq_commander_close_v1.py"
    "scripts\build_a_code_closure_readiness_v1.py"
    "scripts\build_a_code_weekly_ops_summary_v1.py"
    "scripts\Run-ACodeClosureReadinessBundle_v1.ps1"
    "scripts\build_a_code_research_close_migration_draft_v1.py"
    "scripts\Run-ACodeRqCloseCommanderHandoffBundle_v1.ps1"
    "scripts\Invoke-ACodeRqCloseCommanderClose_v1.ps1"
)

$artifacts = @(
    "docs\final\artifacts\a_code_operator_assist_lane_v1_latest.json"
    "docs\final\artifacts\a_code_constitution_worklist_migration_draft_v1.json"
    "reports\a_code_operator_assist_lane_gate_v1_latest.json"
)

$fail = $false
Write-Host "=== A-code operator-assist lane readiness (RQ-031) ===" -ForegroundColor Cyan

foreach ($rel in $scripts) {
    $p = Join-Path $WorkspaceRoot $rel
    if (Test-Path -LiteralPath $p) {
        Write-Host "[OK] $rel" -ForegroundColor Green
    } else {
        Write-Host "[MISS] $rel" -ForegroundColor Red
        $fail = $true
    }
}

foreach ($rel in $artifacts) {
    $p = Join-Path $WorkspaceRoot $rel
    if (Test-Path -LiteralPath $p) {
        Write-Host "[OK] $rel" -ForegroundColor Green
    } else {
        Write-Host "[--] $rel (run operator lane routine)" -ForegroundColor DarkYellow
    }
}

function Test-OperatorLaneTask([string]$Name, [bool]$Required) {
    $taskFail = $false
    $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if ($t) {
        $info = Get-ScheduledTaskInfo -InputObject $t
        $args = [string]$t.Actions[0].Arguments
        $actionOk = ($args -match "Run-ACodeOperatorAssistLaneRoutine_v1\.ps1")
        $lightOk = if ($Name -like "*-Light") { ($args -match "SkipGovernorBundle") } else { -not ($args -match "SkipGovernorBundle") }
        Write-Host "[OK] Task $Name Next=$($info.NextRunTime) action_ok=$actionOk profile_ok=$lightOk" -ForegroundColor Green
        if (-not $actionOk -or -not $lightOk) { $taskFail = $true }
    } elseif ($Required) {
        Write-Host "[MISS] Task $Name (required)" -ForegroundColor Red
        $taskFail = $true
    } else {
        Write-Host "[--] Optional task $Name" -ForegroundColor DarkYellow
    }
    return $taskFail
}

$requireFull = $RequireScheduledTask -or $RequireBothWeeklyTasks
$requireLight = $RequireBothWeeklyTasks
if (Test-OperatorLaneTask -Name $TaskName -Required:$requireFull) { $fail = $true }
if ($RequireBothWeeklyTasks -or (Get-ScheduledTask -TaskName $LightTaskName -ErrorAction SilentlyContinue)) {
    if (Test-OperatorLaneTask -Name $LightTaskName -Required:$requireLight) { $fail = $true }
}

$sched = Join-Path $WorkspaceRoot "reports\a_code_operator_assist_lane_weekly_task_latest.json"
if (Test-Path -LiteralPath $sched) {
    Write-Host "[OK] $sched" -ForegroundColor Green
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
Write-Host "[check] CONSTITUTION §1.2.2 pointer row" -ForegroundColor Cyan
& $py scripts/check_a_code_constitution_pointer_row_v1.py --strict
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] constitution pointer row check" -ForegroundColor Red
    $fail = $true
}

if ($fail) { exit 1 }
Write-Host "[OK] operator-assist lane readiness" -ForegroundColor Green
exit 0
