param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipNewsObservationContractSmoke
)

$ErrorActionPreference = "Stop"

$markRead = Join-Path $WorkspaceRoot "scripts\mark_central_memory_read_v1.py"
$updateHandoff = Join-Path $WorkspaceRoot "scripts\update_ops_handoff_v1.py"
$health = Join-Path $WorkspaceRoot "scripts\run_workspace_automation_health.ps1"
$shadowPnl = Join-Path $WorkspaceRoot "scripts\build_shadow_pnl_guardrail_v1.py"
$bestLoopState = Join-Path $WorkspaceRoot "projects\bitcoin-trading\memory\v2\ops\best_loop_task_state_latest.json"

if (-not (Test-Path -LiteralPath $markRead)) {
    throw "Missing script: $markRead"
}
if (-not (Test-Path -LiteralPath $updateHandoff)) {
    throw "Missing script: $updateHandoff"
}
if (-not (Test-Path -LiteralPath $health)) {
    throw "Missing script: $health"
}
if (-not (Test-Path -LiteralPath $shadowPnl)) {
    throw "Missing script: $shadowPnl"
}

& py $markRead --workspace-root $WorkspaceRoot --reason "longrun_cycle"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$nextAction = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_workspace_automation_health.ps1 -SkipVaultMirror -SkipMkmMemoryInventory -SkipPhase1Readiness -IncludeOperationalReadinessChecklist -IncludeCentralMemoryReadCheck"
if ($SkipNewsObservationContractSmoke) {
    $nextAction += " -SkipNewsObservationContractSmoke"
}

$missionText = "장기기억 기반 24h 안전 자동 루프"
$bestLoopSummary = ""
if (Test-Path -LiteralPath $bestLoopState) {
    try {
        $bl = Get-Content -LiteralPath $bestLoopState -Raw -Encoding UTF8 | ConvertFrom-Json
        $lastAction = [string]$bl.last_action
        $fallback = [string]$bl.fallback_action
        if (-not [string]::IsNullOrWhiteSpace($lastAction) -or -not [string]::IsNullOrWhiteSpace($fallback)) {
            $bestLoopSummary = "$lastAction->$fallback".Trim('-','>')
            $missionText = "$missionText (best_loop: $bestLoopSummary)"
        }
    }
    catch {
        # keep default mission text when best-loop state parse fails
        $bestLoopSummary = "parse_error"
    }
}

& py $updateHandoff --workspace-root $WorkspaceRoot --mission-id "longrun-memory-ops-24h" --mission $missionText --next-action $nextAction --status "in_progress"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$args = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $health,
    "-SkipVaultMirror",
    "-SkipMkmMemoryInventory",
    "-SkipPhase1Readiness",
    "-IncludeOperationalReadinessChecklist",
    "-IncludeCentralMemoryReadCheck"
)
if ($SkipNewsObservationContractSmoke) {
    $args += "-SkipNewsObservationContractSmoke"
}

& powershell @args
$exitCode = $LASTEXITCODE

$shadowArgs = @(
    $shadowPnl,
    "--workspace-root", $WorkspaceRoot,
    "--readiness-json", "docs/final/artifacts/operational_readiness_checklist_v1_latest.json",
    "--briefing-json", "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json",
    "--out", "docs/final/artifacts/shadow_pnl_guardrail_latest.json"
)
if (Test-Path -LiteralPath (Join-Path $WorkspaceRoot "reports/market_pulse_latest.json")) {
    $shadowArgs += @("--price-source-json", "reports/market_pulse_latest.json")
}
& py @shadowArgs
if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
    $exitCode = $LASTEXITCODE
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$logPath = Join-Path $reportDir "longrun_memory_ops_cycle_log.jsonl"
$row = [ordered]@{
    schema = "longrun_memory_ops_cycle_log_v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    workspace_root = $WorkspaceRoot
    skip_news_observation_contract_smoke = [bool]$SkipNewsObservationContractSmoke
    best_loop_summary = $bestLoopSummary
    exit_code = $exitCode
}
($row | ConvertTo-Json -Compress) | Add-Content -LiteralPath $logPath -Encoding UTF8

exit $exitCode

