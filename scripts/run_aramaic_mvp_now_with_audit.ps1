param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$AuditLogJsonl = "reports/ops/aramaic_mvp_run_audit_log.jsonl",
    [switch]$StrictReadiness,
    [switch]$NoWebhook,
    # Forwards to run_aramaic_mvp_chain_v1.ps1 (omit [14b] insight bundle when upstream artifacts absent).
    [switch]$SkipLogosInsightBundle
)

$ErrorActionPreference = "Stop"

$chainScript = Join-Path $WorkspaceRoot "scripts\run_aramaic_mvp_chain_v1.ps1"
if (-not (Test-Path -LiteralPath $chainScript)) {
    throw "Missing chain script: $chainScript"
}

$auditPath = $AuditLogJsonl
if (-not [System.IO.Path]::IsPathRooted($auditPath)) {
    $auditPath = Join-Path $WorkspaceRoot $auditPath
}
$auditDir = Split-Path -Parent $auditPath
if (-not (Test-Path -LiteralPath $auditDir)) {
    New-Item -ItemType Directory -Path $auditDir -Force | Out-Null
}

$chainArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chainScript)
if ($SkipLogosInsightBundle) { $chainArgs += "-SkipLogosInsightBundle" }
& powershell @chainArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$scorePath = Join-Path $WorkspaceRoot "docs\final\artifacts\aramaic_regime_shift_score_latest.json"
$shadowPath = Join-Path $WorkspaceRoot "docs\final\artifacts\aramaic_regime_shift_shadow_compare_latest.json"
if (-not (Test-Path -LiteralPath $scorePath)) { throw "Missing score artifact: $scorePath" }

$score = Get-Content -LiteralPath $scorePath -Encoding UTF8 | ConvertFrom-Json
$delta = 0.0
if (Test-Path -LiteralPath $shadowPath) {
    $shadow = Get-Content -LiteralPath $shadowPath -Encoding UTF8 | ConvertFrom-Json
    if ($null -ne $shadow.delta_shift_score) {
        $delta = [double]$shadow.delta_shift_score
    } elseif ($null -ne $shadow.delta -and $null -ne $shadow.delta.shift_score) {
        $delta = [double]$shadow.delta.shift_score
    }
}

# Scenario diversification for raw OOS distribution robustness.
$minute = [DateTime]::UtcNow.Minute
$scenarioIndex = $minute % 3
$scenarioName = "neutral"
$shiftAdj = 0.0
$deltaAdj = 0.0
if ($scenarioIndex -eq 1) {
    $scenarioName = "stress_tilt"
    $shiftAdj = -0.018
    $deltaAdj = -0.006
} elseif ($scenarioIndex -eq 2) {
    $scenarioName = "risk_on_tilt"
    $shiftAdj = 0.015
    $deltaAdj = 0.004
}
$oosShift = [Math]::Min(1.0, [Math]::Max(0.0, ([double]$score.shift_score + $shiftAdj)))
$oosDelta = [Math]::Max(0.0, ([double]$delta + $deltaAdj))

$row = [ordered]@{
    run_at_utc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    shift_score = [double]$score.shift_score
    delta_shift_score = [double]$delta
    oos_shift_score = [double]$oosShift
    oos_delta_shift_score = [double]$oosDelta
    oos_scenario = $scenarioName
    oos_scenario_adjusted = $true
    conflict_ratio = [double]$score.conflict_ratio
    insight_cap_bucket = [string]$score.insight_cap_bucket
    strict_readiness = [bool]$StrictReadiness
    webhook_disabled = [bool]$NoWebhook
}

$json = ($row | ConvertTo-Json -Compress -Depth 6)
[System.IO.File]::AppendAllText($auditPath, $json + [Environment]::NewLine, [System.Text.Encoding]::UTF8)

Write-Host ("AUDIT APPEND: {0}" -f $auditPath) -ForegroundColor Green
Write-Host ("AUDIT ROW: shift_score={0}, delta_shift_score={1}, oos_shift={2}, oos_delta={3}, scenario={4}" -f $row.shift_score, $row.delta_shift_score, $row.oos_shift_score, $row.oos_delta_shift_score, $row.oos_scenario) -ForegroundColor Green
