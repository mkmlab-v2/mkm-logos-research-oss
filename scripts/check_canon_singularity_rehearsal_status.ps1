# One-minute rehearsal check for canon singularity operations.
# Shows scheduler last result plus the 3 core artifacts:
# - promotion gate
# - delta cutoff autotune
# - delta governance gate
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\check_canon_singularity_rehearsal_status.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\check_canon_singularity_rehearsal_status.ps1 -AsJson

param(
    [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$TaskName = "MKM_CanonSingularity_Chain",
    [string]$OutputJson = "",
    [string]$HistoryJsonl = "",
    [switch]$AppendHistory,
    [switch]$AutoRunStrictOnAlert,
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

function Read-JsonSafe([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    try {
        return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function Read-JsonlLastSafe([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    try {
        $last = Get-Content -LiteralPath $Path -Encoding UTF8 | Select-Object -Last 1
        if ([string]::IsNullOrWhiteSpace($last)) {
            return $null
        }
        return ($last | ConvertFrom-Json)
    }
    catch {
        return $null
    }
}

function Read-JsonlSafe([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return @()
    }
    try {
        $rows = @()
        foreach ($line in (Get-Content -LiteralPath $Path -Encoding UTF8)) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $rows += ,($line | ConvertFrom-Json)
        }
        return $rows
    }
    catch {
        return @()
    }
}

function Count-TailOpsAlerts([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    try {
        $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8)
        $count = 0
        for ($i = $lines.Count - 1; $i -ge 0; $i--) {
            $line = [string]$lines[$i]
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            if ($line -match '"ops_alert_summary"\s*:\s*\{[^}]*"ops_alert"\s*:\s*true') {
                $count += 1
                continue
            }
            break
        }
        return $count
    }
    catch {
        return 0
    }
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

function Append-Utf8NoBom([string]$Path, [string]$Text) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($Path, $Text, $enc)
}

function Query-TaskMeta([string]$Name) {
    try {
        $task = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
        $info = Get-ScheduledTaskInfo -TaskName $Name -ErrorAction Stop
        return @{
            exists = $true
            status = [string]$task.State
            last_result = [string]$info.LastTaskResult
            last_run_time = $(if ($null -ne $info.LastRunTime) { [string]$info.LastRunTime } else { $null })
        }
    }
    catch {
        return @{
            exists = $false
            status = "query_error"
            last_result = $null
            last_run_time = $null
        }
    }
}

$artifacts = Join-Path $WorkspaceRoot "docs\final\artifacts"
$promotionPath = Join-Path $artifacts "original_corpus_regime_singularity_canon_promotion_gate_v1.json"
$autotunePath = Join-Path $artifacts "original_corpus_regime_singularity_canon_delta_cutoff_autotune_v1.json"
$governancePath = Join-Path $artifacts "original_corpus_regime_singularity_canon_delta_cutoff_governance_gate_v1.json"
$autotuneHistoryPath = Join-Path $artifacts "original_corpus_regime_singularity_canon_delta_cutoff_update_history_v1.jsonl"
$driftPath = Join-Path $artifacts "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json"
$freezeV2StabilityPath = Join-Path $artifacts "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json"
$promotionGoNoGoPath = Join-Path $artifacts "original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json"
if (-not $OutputJson -or $OutputJson.Trim().Length -eq 0) {
    $OutputJson = Join-Path $artifacts "original_corpus_regime_singularity_canon_rehearsal_status_latest.json"
}
if (-not $HistoryJsonl -or $HistoryJsonl.Trim().Length -eq 0) {
    $HistoryJsonl = Join-Path $artifacts "original_corpus_regime_singularity_canon_rehearsal_status_history_v1.jsonl"
}

$promotion = Read-JsonSafe -Path $promotionPath
$autotune = Read-JsonSafe -Path $autotunePath
$governance = Read-JsonSafe -Path $governancePath
$drift = Read-JsonSafe -Path $driftPath
$freezeV2Stability = Read-JsonSafe -Path $freezeV2StabilityPath
$promotionGoNoGo = Read-JsonSafe -Path $promotionGoNoGoPath
$autotuneLast = Read-JsonlLastSafe -Path $autotuneHistoryPath
$task = Query-TaskMeta -Name $TaskName
$driftStatus = $(if ($null -ne $drift) { [string]$drift.status } else { "missing" })
$driftStatusNorm = $driftStatus.Trim().ToLowerInvariant()
$driftCount = $(if ($null -ne $drift) { [int]($drift.metrics.drift_count) } else { $null })
$freezeStatus = $(if ($null -ne $freezeV2Stability) { [string]$freezeV2Stability.status } else { "missing" })
$freezeStatusNorm = $freezeStatus.Trim().ToLowerInvariant()
$goNoGoVerdict = $(if ($null -ne $promotionGoNoGo) { [string]$promotionGoNoGo.verdict } else { "missing" })
$goNoGoVerdictNorm = $goNoGoVerdict.Trim().ToLowerInvariant()
$opsAlert = ($driftStatusNorm -eq "alert") -or ($freezeStatusNorm -eq "fail") -or ($goNoGoVerdictNorm -eq "no_go")
$prevConsecutive = Count-TailOpsAlerts -Path $HistoryJsonl
$consecutiveAlert = $(if ($opsAlert) { $prevConsecutive + 1 } else { 0 })
$severity = $(if (-not $opsAlert) { "none" } elseif ($consecutiveAlert -ge 2) { "high" } else { "medium" })
$strictRehearsalScript = Join-Path $WorkspaceRoot "scripts\run_canon_singularity_strict_rehearsal_v1.ps1"
$strictRehearsalSummaryPath = Join-Path $WorkspaceRoot "docs\final\artifacts\original_corpus_regime_singularity_canon_strict_rehearsal_run_v1.json"
$recommendedCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$strictRehearsalScript`" -SkipVaultSync"
$strictAutoRun = [ordered]@{
    enabled = [bool]$AutoRunStrictOnAlert
    triggered = $false
    exit_code = $null
    status = "not_run"
    summary_path = $strictRehearsalSummaryPath
}
if ($opsAlert -and $AutoRunStrictOnAlert -and (Test-Path -LiteralPath $strictRehearsalScript)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $strictRehearsalScript -SkipVaultSync -AppendHistory
    $strictExit = $LASTEXITCODE
    $strictAutoRun.triggered = $true
    $strictAutoRun.exit_code = [int]$strictExit
    $strictAutoRun.status = $(if ($strictExit -eq 0) { "pass" } else { "fail" })
}

$report = [ordered]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    task = [ordered]@{
        name = $TaskName
        exists = [bool]$task.exists
        status = $task.status
        last_result = $task.last_result
        last_run_time = $task.last_run_time
    }
    promotion_gate = [ordered]@{
        path = $promotionPath
        status = $(if ($null -ne $promotion) { [string]$promotion.status } else { "missing" })
        generated_at_utc = $(if ($null -ne $promotion) { [string]$promotion.generated_at_utc } else { $null })
    }
    delta_cutoff_autotune = [ordered]@{
        path = $autotunePath
        status = $(if ($null -ne $autotune) { [string]$autotune.status } else { "missing" })
        generated_at_utc = $(if ($null -ne $autotune) { [string]$autotune.generated_at_utc } else { $null })
        current_min_score_delta = $(if ($null -ne $autotune) { $autotune.inputs.current_min_score_delta } else { $null })
        applied_min_score_delta = $(if ($null -ne $autotune) { $autotune.metrics.applied_min_score_delta } else { $null })
        apply_reason = $(if ($null -ne $autotune) { [string]$autotune.metrics.apply_reason } else { $null })
    }
    delta_governance_gate = [ordered]@{
        path = $governancePath
        status = $(if ($null -ne $governance) { [string]$governance.status } else { "missing" })
        generated_at_utc = $(if ($null -ne $governance) { [string]$governance.generated_at_utc } else { $null })
        apply_rate = $(if ($null -ne $governance) { $governance.metrics.apply_rate } else { $null })
        hold_streak = $(if ($null -ne $governance) { $governance.metrics.hold_streak } else { $null })
        in_grace_window = $(if ($null -ne $governance) { $governance.metrics.in_grace_window } else { $null })
    }
    delta_autotune_history_latest = [ordered]@{
        path = $autotuneHistoryPath
        generated_at_utc = $(if ($null -ne $autotuneLast) { [string]$autotuneLast.generated_at_utc } else { $null })
        status = $(if ($null -ne $autotuneLast) { [string]$autotuneLast.status } else { "missing" })
        applied_min_score_delta = $(if ($null -ne $autotuneLast) { $autotuneLast.applied_min_score_delta } else { $null })
        apply_reason = $(if ($null -ne $autotuneLast) { [string]$autotuneLast.apply_reason } else { $null })
    }
    drift_gate = [ordered]@{
        path = $driftPath
        status = $driftStatus
        drift_count = $driftCount
        generated_at_utc = $(if ($null -ne $drift) { [string]$drift.generated_at_utc } else { $null })
    }
    freeze_v2_stability_gate = [ordered]@{
        path = $freezeV2StabilityPath
        status = $(if ($null -ne $freezeV2Stability) { [string]$freezeV2Stability.status } else { "missing" })
        generated_at_utc = $(if ($null -ne $freezeV2Stability) { [string]$freezeV2Stability.generated_at_utc } else { $null })
        window_size = $(if ($null -ne $freezeV2Stability) { $freezeV2Stability.metrics.window_size } else { $null })
        frozen_rate = $(if ($null -ne $freezeV2Stability) { $freezeV2Stability.metrics.frozen_rate } else { $null })
    }
    promotion_go_no_go = [ordered]@{
        path = $promotionGoNoGoPath
        verdict = $goNoGoVerdict
        generated_at_utc = $(if ($null -ne $promotionGoNoGo) { [string]$promotionGoNoGo.generated_at_utc } else { $null })
        hold_reasons = $(if ($null -ne $promotionGoNoGo) { @($promotionGoNoGo.hold_reasons) } else { @() })
    }
    ops_alert_summary = [ordered]@{
        ops_alert = [bool]$opsAlert
        severity = $severity
        consecutive_alert_count = $consecutiveAlert
        strict_rehearsal_recommended = [bool]$opsAlert
    }
    recommended_action = [ordered]@{
        kind = $(if ($opsAlert) { "run_strict_rehearsal" } else { "none" })
        command = $(if ($opsAlert) { $recommendedCommand } else { "" })
        reason = $(if (-not $opsAlert) { "stable" } elseif ($driftStatusNorm -eq "alert") { "drift_gate_alert" } elseif ($freezeStatusNorm -eq "fail") { "freeze_v2_stability_fail" } else { "promotion_go_no_go_no_go" })
    }
    strict_auto_run = $strictAutoRun
}

$reportJson = $report | ConvertTo-Json -Depth 8
$outDir = Split-Path -Parent $OutputJson
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
Write-Utf8NoBom -Path $OutputJson -Text ($reportJson + [Environment]::NewLine)
if ($AppendHistory) {
    $histDir = Split-Path -Parent $HistoryJsonl
    if ($histDir -and -not (Test-Path -LiteralPath $histDir)) {
        New-Item -ItemType Directory -Path $histDir -Force | Out-Null
    }
    $line = ($report | ConvertTo-Json -Depth 8 -Compress) + [Environment]::NewLine
    Append-Utf8NoBom -Path $HistoryJsonl -Text $line
}

if ($AsJson) {
    $reportJson
    exit 0
}

Write-Host "== Canon Singularity Rehearsal Check =="
Write-Host ("Task: {0} | status={1} | last_result={2} | last_run={3}" -f $report.task.name, $report.task.status, $report.task.last_result, $report.task.last_run_time)
Write-Host ("Promotion gate: status={0} | generated_at={1}" -f $report.promotion_gate.status, $report.promotion_gate.generated_at_utc)
Write-Host ("Delta autotune: status={0} | current={1} -> applied={2} | reason={3}" -f $report.delta_cutoff_autotune.status, $report.delta_cutoff_autotune.current_min_score_delta, $report.delta_cutoff_autotune.applied_min_score_delta, $report.delta_cutoff_autotune.apply_reason)
Write-Host ("Delta governance: status={0} | apply_rate={1} | hold_streak={2} | grace={3}" -f $report.delta_governance_gate.status, $report.delta_governance_gate.apply_rate, $report.delta_governance_gate.hold_streak, $report.delta_governance_gate.in_grace_window)
Write-Host ("Autotune history latest: status={0} | generated_at={1}" -f $report.delta_autotune_history_latest.status, $report.delta_autotune_history_latest.generated_at_utc)
Write-Host ("Drift gate: status={0} | drift_count={1}" -f $report.drift_gate.status, $report.drift_gate.drift_count)
Write-Host ("Freeze v2 stability: status={0} | frozen_rate={1} | window_size={2}" -f $report.freeze_v2_stability_gate.status, $report.freeze_v2_stability_gate.frozen_rate, $report.freeze_v2_stability_gate.window_size)
Write-Host ("Promotion Go/No-Go: verdict={0}" -f $report.promotion_go_no_go.verdict)
Write-Host ("Ops alert: enabled={0} | severity={1} | consecutive={2}" -f $report.ops_alert_summary.ops_alert, $report.ops_alert_summary.severity, $report.ops_alert_summary.consecutive_alert_count)
if ($report.recommended_action.kind -ne "none") {
    Write-Host ("Recommended action: {0}" -f $report.recommended_action.command)
}
if ($report.strict_auto_run.triggered) {
    Write-Host ("Strict auto-run: status={0} | exit_code={1}" -f $report.strict_auto_run.status, $report.strict_auto_run.exit_code)
}
Write-Host ("Rehearsal latest JSON: {0}" -f $OutputJson)
if ($AppendHistory) {
    Write-Host ("Rehearsal history JSONL append: {0}" -f $HistoryJsonl)
}
