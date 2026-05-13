# Run Aramaic MVP now+audit in a loop until target audit runs are reached.
# Optional -SkipLogosInsightBundle forwards to run_aramaic_mvp_now_with_audit.ps1 (same as chain [14b] skip).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$AuditLogJsonl = "reports/ops/aramaic_mvp_run_audit_log.jsonl",
    [int]$TargetAuditRuns = 50,
    [int]$MaxIterations = 50,
    [int]$SleepSecondsBetweenRuns = 0,
    [switch]$StrictReadiness,
    [switch]$NoWebhook,
    [switch]$SkipIngestAndReadiness,
    [switch]$SkipLogosInsightBundle
)

$ErrorActionPreference = "Stop"

$runnerScript = Join-Path $WorkspaceRoot "scripts\run_aramaic_mvp_now_with_audit.ps1"
$ingestScript = Join-Path $WorkspaceRoot "scripts\ingest_two_track_raw_oos_from_audit_v1.py"
$readinessScript = Join-Path $WorkspaceRoot "scripts\report_two_track_raw_oos_readiness_v1.py"

if (-not (Test-Path -LiteralPath $runnerScript)) { throw "Missing runner script: $runnerScript" }
if (-not (Test-Path -LiteralPath $ingestScript)) { throw "Missing ingest script: $ingestScript" }
if (-not (Test-Path -LiteralPath $readinessScript)) { throw "Missing readiness script: $readinessScript" }

function Get-AuditRuns([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return 0 }
    $count = 0
    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        if (-not [string]::IsNullOrWhiteSpace($line)) { $count++ }
    }
    return $count
}

$logPath = $AuditLogJsonl
if (-not [System.IO.Path]::IsPathRooted($logPath)) {
    $logPath = Join-Path $WorkspaceRoot $logPath
}

$startRuns = Get-AuditRuns -Path $logPath
Write-Host ("START: audit_runs={0}, target={1}, max_iterations={2}" -f $startRuns, $TargetAuditRuns, $MaxIterations) -ForegroundColor Cyan

for ($i = 1; $i -le $MaxIterations; $i++) {
    $currentRuns = Get-AuditRuns -Path $logPath
    if ($currentRuns -ge $TargetAuditRuns) {
        Write-Host ("DONE: target met before iteration. audit_runs={0}" -f $currentRuns) -ForegroundColor Green
        break
    }

    Write-Host ("[{0}/{1}] Run immediate chain+audit (current={2}, target={3})" -f $i, $MaxIterations, $currentRuns, $TargetAuditRuns) -ForegroundColor Yellow
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $runnerScript, "-WorkspaceRoot", $WorkspaceRoot, "-AuditLogJsonl", $logPath)
    if ($StrictReadiness) { $args += "-StrictReadiness" }
    if ($NoWebhook) { $args += "-NoWebhook" }
    if ($SkipLogosInsightBundle) { $args += "-SkipLogosInsightBundle" }
    & powershell @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SkipIngestAndReadiness) {
        & py $ingestScript "--audit-jsonl" $logPath "--benchmark-json" "docs/final/artifacts/two_track_benchmark_comparison_latest.json" "--input-jsonl" "docs/final/artifacts/two_track_raw_oos_samples_latest.jsonl" "--output-jsonl" "docs/final/artifacts/two_track_raw_oos_samples_latest.jsonl" "--min-samples-per-baseline" "$TargetAuditRuns"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & py $readinessScript "--raw-oos-jsonl" "docs/final/artifacts/two_track_raw_oos_samples_latest.jsonl" "--benchmark-json" "docs/final/artifacts/two_track_benchmark_comparison_latest.json" "--output-json" "docs/final/artifacts/two_track_raw_oos_readiness_latest.json" "--audit-log-jsonl" $logPath "--min-samples-per-baseline" "$TargetAuditRuns"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (($SleepSecondsBetweenRuns -gt 0) -and ($i -lt $MaxIterations)) {
        Start-Sleep -Seconds $SleepSecondsBetweenRuns
    }
}

$finalRuns = Get-AuditRuns -Path $logPath
Write-Host ("END: audit_runs={0}, target={1}, delta_added={2}" -f $finalRuns, $TargetAuditRuns, [Math]::Max(0, $finalRuns - $startRuns)) -ForegroundColor Green
