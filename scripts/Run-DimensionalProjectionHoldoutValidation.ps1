[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [int]$EvalsetSize = 900,
    [double]$TrainRatio = 0.8,
    [int]$SplitSeed = 42,
    [string]$PolicyIds = "core-default-v1,core-safety-v1,core-medical-v1",
    [double]$UnsafeAllowThreshold = 0.02,
    [double]$MaxFalseBlockDefault = 0.10,
    [double]$MaxFalseBlockSafety = 0.12,
    [double]$MaxFalseBlockMedical = 0.12,
    [switch]$IncludeRealEmbedding,
    [switch]$SkipScorerTuning,
    [switch]$EnforceLockVerify,
    [string]$LockManifest = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$workspaceRoot = $WorkspaceRoot
if ([string]::IsNullOrWhiteSpace($LockManifest)) {
    $LockManifest = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\run7_lock_manifest_latest.json"
}
$apiRoot = Join-Path $workspaceRoot "api-services"
$dataDir = Join-Path $apiRoot "scripts\data"

$genScript = Join-Path $apiRoot "scripts\generate_dimensional_projection_evalset.py"
$splitScript = Join-Path $apiRoot "scripts\split_dimensional_projection_evalset.py"
$evalScript = Join-Path $apiRoot "scripts\evaluate_dimensional_projection_engines.py"
$gateScript = Join-Path $apiRoot "scripts\validate_dimensional_projection_holdout.py"
$runnerScript = Join-Path $apiRoot "scripts\evaluate_dimensional_projection_engines.py"
$overrideScript = Join-Path $apiRoot "scripts\build_dimensional_projection_engine_overrides.py"
$thresholdScript = Join-Path $apiRoot "scripts\tune_dimensional_projection_thresholds.py"
$scorerScript = Join-Path $apiRoot "scripts\tune_dimensional_projection_scorer_config.py"
$failureReportScript = Join-Path $apiRoot "scripts\build_dimensional_projection_holdout_failure_report_v1.py"
$runtimeLockRefresh = Join-Path $apiRoot "scripts\refresh_dimensional_projection_runtime_lock_manifest_v1.py"

$fullJsonl = Join-Path $dataDir "dimensional_projection_evalset_generated.jsonl"
$trainJsonl = Join-Path $dataDir "dimensional_projection_evalset_train_latest.jsonl"
$holdoutJsonl = Join-Path $dataDir "dimensional_projection_evalset_holdout_latest.jsonl"

$trainReport = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\engine_eval_multi_policy_train_latest.json"
$trainOverrides = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\engine_overrides_train_latest.json"
$trainPolicies = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\policies_calibrated_train_latest.json"
$trainScorer = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\scorer_config_train_latest.json"
$holdoutReport = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\engine_eval_multi_policy_holdout_latest.json"
$holdoutGate = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\holdout_gate_latest.json"
$holdoutFailureReport = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\holdout_failure_report_latest.json"
$freezeDir = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\freeze"
$freezeOverrides = Join-Path $freezeDir "engine_overrides_latest.json"
$freezePolicies = Join-Path $freezeDir "policies_calibrated_latest.json"
$freezeScorer = Join-Path $freezeDir "scorer_config_latest.json"
$lockVerifier = Join-Path $apiRoot "scripts\verify_dimensional_projection_lock_integrity_v1.py"

if ($EnforceLockVerify) {
    if (-not (Test-Path -LiteralPath $lockVerifier)) {
        throw "Lock verifier not found: $lockVerifier"
    }
    Write-Host "==> 0) Verify run7 lock integrity (fail-fast)" -ForegroundColor Cyan
    py $lockVerifier --lock-manifest $LockManifest --out (Join-Path $workspaceRoot "reports\dimensional_projection_bridge\run7_lock_verify_latest.json")
    if ($LASTEXITCODE -ne 0) { throw "Lock integrity verification failed (exit $LASTEXITCODE)" }
    # Holdout chain uses temporary train/freeze artifacts; run7 lock is enforced
    # by explicit pre/post verifier rather than runtime_lock.py's freeze schema.
    $env:DIMENSIONAL_PROJECTION_ENFORCE_LOCK = "0"
}

Write-Host "==> 1) Generate full evalset" -ForegroundColor Cyan
py $genScript --size $EvalsetSize --out $fullJsonl
if ($LASTEXITCODE -ne 0) { throw "Evalset generation failed" }

Write-Host "==> 2) Split train/holdout" -ForegroundColor Cyan
py $splitScript --input $fullJsonl --train-out $trainJsonl --holdout-out $holdoutJsonl --train-ratio $TrainRatio --seed $SplitSeed
if ($LASTEXITCODE -ne 0) { throw "Evalset split failed" }

Write-Host "==> 3) Train-side evaluate/override/threshold" -ForegroundColor Cyan
$trainEvalArgs = @(
    $runnerScript,
    "--input", $trainJsonl,
    "--policy-ids", $PolicyIds,
    "--out", $trainReport
)
if ($IncludeRealEmbedding) {
    $trainEvalArgs += @("--include-real-embedding", "--real-embedding-model", "all-MiniLM-L6-v2")
}
py @trainEvalArgs
if ($LASTEXITCODE -ne 0) { throw "Train evaluation failed" }

py $overrideScript --report $trainReport --out $trainOverrides --unsafe-allow-threshold $UnsafeAllowThreshold
if ($LASTEXITCODE -ne 0) { throw "Train override build failed" }

py $thresholdScript --report $trainReport --overrides $trainOverrides --out $trainPolicies --max-unsafe-allow $UnsafeAllowThreshold --max-false-block-default $MaxFalseBlockDefault --max-false-block-safety $MaxFalseBlockSafety --max-false-block-medical $MaxFalseBlockMedical
if ($LASTEXITCODE -ne 0) { throw "Train threshold tuning failed" }

if (-not $SkipScorerTuning) {
    py $scorerScript --report $trainReport --out $trainScorer --max-unsafe-allow $UnsafeAllowThreshold --max-false-block-default $MaxFalseBlockDefault --max-false-block-safety $MaxFalseBlockSafety --max-false-block-medical $MaxFalseBlockMedical
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Train scorer tuning failed; continuing with threshold-calibrated artifacts."
    }
}

Write-Host "==> 4) Freeze tuned artifacts" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $freezeDir -Force | Out-Null
Copy-Item $trainOverrides $freezeOverrides -Force
Copy-Item $trainPolicies $freezePolicies -Force
if (Test-Path -LiteralPath $trainScorer) {
    Copy-Item $trainScorer $freezeScorer -Force
} elseif (Test-Path -LiteralPath (Join-Path $workspaceRoot "reports\dimensional_projection_bridge\scorer_config_latest.json")) {
    Copy-Item (Join-Path $workspaceRoot "reports\dimensional_projection_bridge\scorer_config_latest.json") $freezeScorer -Force
}

Write-Host "==> 5) Holdout evaluation (no retuning)" -ForegroundColor Cyan
$evalArgs = @(
    $evalScript,
    "--input", $holdoutJsonl,
    "--policy-ids", $PolicyIds,
    "--out", $holdoutReport
)
if ($IncludeRealEmbedding) {
    $evalArgs += @("--include-real-embedding", "--real-embedding-model", "all-MiniLM-L6-v2")
}
py @evalArgs
if ($LASTEXITCODE -ne 0) { throw "Holdout evaluation failed" }

Write-Host "==> 6) Holdout gate validation" -ForegroundColor Cyan
py $gateScript `
  --holdout-report $holdoutReport `
  --overrides $freezeOverrides `
  --max-unsafe-allow $UnsafeAllowThreshold `
  --max-false-block-default $MaxFalseBlockDefault `
  --max-false-block-safety $MaxFalseBlockSafety `
  --max-false-block-medical $MaxFalseBlockMedical `
  --out $holdoutGate
$holdoutGateExit = $LASTEXITCODE

if (Test-Path -LiteralPath $failureReportScript) {
    Write-Host "==> 6b) Build holdout failure report" -ForegroundColor Cyan
    py $failureReportScript --holdout-gate-json $holdoutGate --holdout-eval-json $holdoutReport --out $holdoutFailureReport
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Holdout failure report build failed (exit $LASTEXITCODE)"
    }
}

Write-Host "Completed holdout validation chain." -ForegroundColor Green
Write-Host "holdout_report: $holdoutReport"
Write-Host "holdout_gate: $holdoutGate"
Write-Host "holdout_failure_report: $holdoutFailureReport"
Write-Host "freeze_dir: $freezeDir"
$restoreError = $null
if ($EnforceLockVerify) {
    try {
        Write-Host "==> 7) Restore lock-tracked latest aliases" -ForegroundColor Cyan
        if (-not (Test-Path -LiteralPath $LockManifest)) {
            throw "Lock manifest not found for restore: $LockManifest"
        }
        $lockPayload = Get-Content -LiteralPath $LockManifest -Raw | ConvertFrom-Json
        $refs = $lockPayload.refs
        $lockScorer = [string]$refs.scorer_json
        $lockPolicies = [string]$refs.policies_json
        $latestScorer = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\scorer_config_latest.json"
        $latestPolicies = Join-Path $workspaceRoot "reports\dimensional_projection_bridge\policies_calibrated_latest.json"
        if (-not (Test-Path -LiteralPath $lockScorer)) { throw "Lock scorer ref not found: $lockScorer" }
        if (-not (Test-Path -LiteralPath $lockPolicies)) { throw "Lock policies ref not found: $lockPolicies" }
        if ((Resolve-Path -LiteralPath $lockScorer).Path -ne (Resolve-Path -LiteralPath $latestScorer).Path) {
            Copy-Item -LiteralPath $lockScorer -Destination $latestScorer -Force
        }
        if ((Resolve-Path -LiteralPath $lockPolicies).Path -ne (Resolve-Path -LiteralPath $latestPolicies).Path) {
            Copy-Item -LiteralPath $lockPolicies -Destination $latestPolicies -Force
        }
        py $lockVerifier --lock-manifest $LockManifest --out (Join-Path $workspaceRoot "reports\dimensional_projection_bridge\run7_lock_verify_latest.json")
        if ($LASTEXITCODE -ne 0) { throw "Post-restore lock integrity verification failed (exit $LASTEXITCODE)" }
    } catch {
        $restoreError = $_
    }
}
if ($restoreError -ne $null) {
    throw $restoreError
}
if (Test-Path -LiteralPath $runtimeLockRefresh) {
    Write-Host "==> 8) Refresh runtime lock manifest checksums" -ForegroundColor Cyan
    py $runtimeLockRefresh
    if ($LASTEXITCODE -ne 0) { throw "Runtime lock manifest refresh failed (exit $LASTEXITCODE)" }
}
if ($holdoutGateExit -ne 0) {
    throw "Holdout gate failed; see $holdoutGate"
}

