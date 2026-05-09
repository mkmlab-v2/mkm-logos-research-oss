[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipOrchestratorRun,
    [switch]$EnableAutoDemotion,
    [switch]$EnableAutoPromotion,
    [int]$AutoPromotionMinGoStreak = 3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$py = "py"
$orch = Join-Path $WorkspaceRoot "scripts\mkm_global_orchestrator_v1.py"
$check = Join-Path $WorkspaceRoot "scripts\check_mkm_orchestrator_go_stability_v1.py"
$alert = Join-Path $WorkspaceRoot "scripts\send_mkm_orchestrator_down_transition_alert_v1.py"
$demote = Join-Path $WorkspaceRoot "scripts\auto_demote_mkm_orchestrator_policy_v1.py"
$promote = Join-Path $WorkspaceRoot "scripts\auto_promote_mkm_orchestrator_policy_v1.py"
$out = Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_global_orchestrator_go_stability_latest.json"
$cycleLog = Join-Path $WorkspaceRoot "reports\mkm_orchestrator_go_cycle_log.jsonl"

if (-not (Test-Path -LiteralPath $check)) {
    throw "Missing script: $check"
}
if (-not (Test-Path -LiteralPath $alert)) {
    throw "Missing script: $alert"
}
if ($EnableAutoDemotion -and -not (Test-Path -LiteralPath $demote)) {
    throw "Missing script: $demote"
}
if ($EnableAutoPromotion -and -not (Test-Path -LiteralPath $promote)) {
    throw "Missing script: $promote"
}
if ((-not $SkipOrchestratorRun) -and (-not (Test-Path -LiteralPath $orch))) {
    throw "Missing script: $orch"
}

if (-not $SkipOrchestratorRun) {
    & $py $orch
    if ($LASTEXITCODE -ne 0) {
        throw "mkm_global_orchestrator_v1.py failed with exit code $LASTEXITCODE"
    }
}

& $py $check
$checkExit = $LASTEXITCODE

# Always advance previous snapshot for next transition comparison.
& $py $check --refresh-previous
$refreshExit = $LASTEXITCODE
if ($refreshExit -ne 0 -and $refreshExit -ne 1) {
    throw "check_mkm_orchestrator_go_stability_v1.py --refresh-previous failed with exit code $refreshExit"
}

& $py $alert --stability-json $out
$alertExit = $LASTEXITCODE
if ($alertExit -ne 0) {
    throw "send_mkm_orchestrator_down_transition_alert_v1.py failed with exit code $alertExit"
}

if ($EnableAutoDemotion) {
    & $py $demote --stability-json $out
    $demoteExit = $LASTEXITCODE
    if ($demoteExit -ne 0) {
        throw "auto_demote_mkm_orchestrator_policy_v1.py failed with exit code $demoteExit"
    }
    Write-Output "auto_demotion=enabled"
}
else {
    Write-Output "auto_demotion=disabled"
}

if ($EnableAutoPromotion) {
    & $py $promote --stability-json $out --min-go-streak $AutoPromotionMinGoStreak
    $promoteExit = $LASTEXITCODE
    if ($promoteExit -ne 0) {
        throw "auto_promote_mkm_orchestrator_policy_v1.py failed with exit code $promoteExit"
    }
    Write-Output "auto_promotion=enabled"
    Write-Output "auto_promotion_min_go_streak=$AutoPromotionMinGoStreak"
}
else {
    Write-Output "auto_promotion=disabled"
}

$stabilityObj = Get-Content -LiteralPath $out -Raw -Encoding UTF8 | ConvertFrom-Json
$currentDecision = [string]$stabilityObj.current_decision
$previousDecision = [string]$stabilityObj.previous_decision
$transition = [string]$stabilityObj.transition
$goStable = [bool]$stabilityObj.go_stable
$downTransition = [bool]$stabilityObj.down_transition_detected

$logRow = @{
    schema = "mkm_orchestrator_go_cycle_log_v1"
    ts_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    current_decision = $currentDecision
    previous_decision = $previousDecision
    transition = $transition
    go_stable = $goStable
    down_transition_detected = $downTransition
    auto_demotion_enabled = [bool]$EnableAutoDemotion
    auto_promotion_enabled = [bool]$EnableAutoPromotion
    auto_promotion_min_go_streak = [int]$AutoPromotionMinGoStreak
}
$logLine = $logRow | ConvertTo-Json -Compress
$logDir = Split-Path -Parent $cycleLog
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
Add-Content -LiteralPath $cycleLog -Value $logLine -Encoding UTF8

Write-Output "stability_report=$out"
Write-Output "cycle_log_jsonl=$cycleLog"
Write-Output "go_stability_exit_code=$checkExit"
if ($checkExit -eq 0) {
    Write-Output "go_stability_status=stable"
}
else {
    Write-Output "go_stability_status=down_transition_or_not_go"
}

exit $checkExit
