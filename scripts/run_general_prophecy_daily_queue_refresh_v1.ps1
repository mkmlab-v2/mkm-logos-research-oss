# Daily lightweight refresh for General Prophecy queue artifacts.
# Restores legacy task entrypoint: \GeneralProphecyDailyQueueV1
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [ValidateSet("research", "ops")]
    [string]$HoldoutGateProfile = "research",
    [double]$MyeongniHoldConfidenceCut = 0.36,
    [double]$MyeongniReduceDirectionCut = 0.45,
    [double]$MyeongniReduceConfidenceCut = 0.64,
    [ValidateSet("true", "false")]
    [string]$IncludeLogosV2 = "true",
    [ValidateSet("true", "false")]
    [string]$EnableLogosResponseV1Retry = "false",
    [ValidateSet("true", "false")]
    [string]$EnableLogosResponseQualityScore = "true",
    [ValidateSet("true", "false")]
    [string]$EnableLogosResponseQualityAlert = "true",
    [double]$LogosResponseQualityMinOverall = 8.0,
    [string]$LogosResponseV1PrimaryInput = "docs/final/artifacts/logos_response_v1_llm_raw_latest.txt",
    [string]$LogosResponseV1RetryInput = "docs/final/artifacts/logos_response_v1_llm_retry_latest.txt",
    [int]$LogosResponseV1MaxAttempts = 2
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$failureOut = Join-Path $WorkspaceRoot "docs\final\artifacts\general_prophecy_daily_queue_failure_summary_latest.json"
$includeLogosV2Flag = $IncludeLogosV2 -eq "true"
$enableLogosResponseV1RetryFlag = $EnableLogosResponseV1Retry -eq "true"
$enableLogosResponseQualityScoreFlag = $EnableLogosResponseQualityScore -eq "true"
$enableLogosResponseQualityAlertFlag = $EnableLogosResponseQualityAlert -eq "true"

function Write-FailureSummary([string]$Step, [int]$ExitCode) {
    $doc = [ordered]@{
        schema = "general_prophecy_daily_queue_failure_summary_v1"
        ts_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        holdout_gate_profile = $HoldoutGateProfile
        failed_step = $Step
        exit_code = $ExitCode
    }
    $dir = Split-Path -Parent $failureOut
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $doc | ConvertTo-Json -Depth 5 | Out-File -LiteralPath $failureOut -Encoding utf8
}

function Invoke-Step([string]$Step, [scriptblock]$Block) {
    & $Block
    if ($LASTEXITCODE -ne 0) {
        Write-FailureSummary -Step $Step -ExitCode $LASTEXITCODE
        exit $LASTEXITCODE
    }
}

$gen = Join-Path $WorkspaceRoot "scripts\generate_general_prophecy_v1.py"
$brief = Join-Path $WorkspaceRoot "scripts\build_general_prophecy_brief.py"
$brier = Join-Path $WorkspaceRoot "scripts\eval_general_prophecy_brier_score.py"
$explainable = Join-Path $WorkspaceRoot "scripts\build_general_prophecy_explainable_v1.py"
$quality = Join-Path $WorkspaceRoot "scripts\report_general_prophecy_explainability_quality_v1.py"
$holdout = Join-Path $WorkspaceRoot "scripts\build_general_prophecy_explainability_holdout_report_v1.py"
$holdoutGate = Join-Path $WorkspaceRoot "scripts\check_general_prophecy_explainability_holdout_gate_v1.py"
$holdoutCandidates = Join-Path $WorkspaceRoot "scripts\build_general_prophecy_holdout_evolution_candidates_v1.py"
$holdoutAblation = Join-Path $WorkspaceRoot "scripts\run_general_prophecy_holdout_evolution_ablation_v1.py"
$holdoutAlert = Join-Path $WorkspaceRoot "scripts\alert_general_prophecy_holdout_gate_v1.py"
$myeongniGate = Join-Path $WorkspaceRoot "scripts\build_myeongni_promotion_go_nogo_v1.py"
$mkmMyeongniV2 = Join-Path $WorkspaceRoot "scripts\build_mkm_myeongni_response_v2.py"
$mkmMyeongniV2Validate = Join-Path $WorkspaceRoot "scripts\validate_mkm_myeongni_response_v2.py"
$mkmLogosV2 = Join-Path $WorkspaceRoot "scripts\build_mkm_logos_response_v2.py"
$mkmLogosV2Validate = Join-Path $WorkspaceRoot "scripts\validate_mkm_logos_response_v2.py"
$logosResponseV1InputBuilder = Join-Path $WorkspaceRoot "scripts\build_logos_response_retry_inputs_v1.py"
$logosResponseV1Retry = Join-Path $WorkspaceRoot "scripts\run_logos_response_retry_pipeline_v1.py"
$logosResponseQualityScore = Join-Path $WorkspaceRoot "scripts\build_logos_response_quality_score_v1.py"
$logosResponseQualityAlert = Join-Path $WorkspaceRoot "scripts\alert_logos_response_quality_score_v1.py"
$logosBriefPath = "docs/final/artifacts/logos_symbolic_paid_user_brief_latest.md"
$notebookManifestPath = "docs/NotebookLM_sources_manifest.md"

if (-not (Test-Path -LiteralPath $gen)) { throw "Missing script: $gen" }
if (-not (Test-Path -LiteralPath $brief)) { throw "Missing script: $brief" }
if (-not (Test-Path -LiteralPath $brier)) { throw "Missing script: $brier" }
if (-not (Test-Path -LiteralPath $explainable)) { throw "Missing script: $explainable" }
if (-not (Test-Path -LiteralPath $quality)) { throw "Missing script: $quality" }
if (-not (Test-Path -LiteralPath $holdout)) { throw "Missing script: $holdout" }
if (-not (Test-Path -LiteralPath $holdoutGate)) { throw "Missing script: $holdoutGate" }
if (-not (Test-Path -LiteralPath $holdoutCandidates)) { throw "Missing script: $holdoutCandidates" }
if (-not (Test-Path -LiteralPath $holdoutAblation)) { throw "Missing script: $holdoutAblation" }
if (-not (Test-Path -LiteralPath $holdoutAlert)) { throw "Missing script: $holdoutAlert" }
if (-not (Test-Path -LiteralPath $myeongniGate)) { throw "Missing script: $myeongniGate" }
if (-not (Test-Path -LiteralPath $mkmMyeongniV2)) { throw "Missing script: $mkmMyeongniV2" }
if (-not (Test-Path -LiteralPath $mkmMyeongniV2Validate)) { throw "Missing script: $mkmMyeongniV2Validate" }
if ($includeLogosV2Flag -and (-not (Test-Path -LiteralPath $mkmLogosV2))) { throw "Missing script: $mkmLogosV2" }
if ($includeLogosV2Flag -and (-not (Test-Path -LiteralPath $mkmLogosV2Validate))) { throw "Missing script: $mkmLogosV2Validate" }
if ($enableLogosResponseV1RetryFlag -and (-not (Test-Path -LiteralPath $logosResponseV1InputBuilder))) { throw "Missing script: $logosResponseV1InputBuilder" }
if ($enableLogosResponseV1RetryFlag -and (-not (Test-Path -LiteralPath $logosResponseV1Retry))) { throw "Missing script: $logosResponseV1Retry" }
if ($enableLogosResponseV1RetryFlag -and $enableLogosResponseQualityScoreFlag -and (-not (Test-Path -LiteralPath $logosResponseQualityScore))) { throw "Missing script: $logosResponseQualityScore" }
if ($enableLogosResponseV1RetryFlag -and $enableLogosResponseQualityScoreFlag -and $enableLogosResponseQualityAlertFlag -and (-not (Test-Path -LiteralPath $logosResponseQualityAlert))) { throw "Missing script: $logosResponseQualityAlert" }

Invoke-Step "generate_general_prophecy" {
    & py -3 $gen --output "docs/final/artifacts/general_prophecy_latest.json" --stub-forecasts
}

Invoke-Step "build_general_prophecy_brief" {
    & py -3 $brief --input "docs/final/artifacts/general_prophecy_latest.json" --output "docs/final/artifacts/general_prophecy_brief_latest.md"
}

Invoke-Step "eval_general_prophecy_brier" {
    & py -3 $brier --input "docs/final/artifacts/general_prophecy_latest.json" --output "docs/final/artifacts/general_prophecy_brier_eval_latest.json"
}

Invoke-Step "build_general_prophecy_explainable" {
    & py -3 $explainable --input "docs/final/artifacts/general_prophecy_latest.json" --output "docs/final/artifacts/general_prophecy_explainable_latest.json"
}

Invoke-Step "report_explainability_quality" {
    & py -3 $quality --input "docs/final/artifacts/general_prophecy_explainable_latest.json" --output "docs/final/artifacts/general_prophecy_explainability_quality_v1_latest.json"
}

Invoke-Step "build_explainability_holdout_report" {
    & py -3 $holdout --input "docs/final/artifacts/general_prophecy_explainability_quality_v1_latest.json" --output "docs/final/artifacts/general_prophecy_explainability_holdout_report_v1_latest.json"
}

Invoke-Step "check_explainability_holdout_gate" {
    & py -3 $holdoutGate --holdout-json "docs/final/artifacts/general_prophecy_explainability_holdout_report_v1_latest.json" --output-json "docs/final/artifacts/general_prophecy_explainability_holdout_gate_v1_latest.json" --profile $HoldoutGateProfile
}

Invoke-Step "build_holdout_evolution_candidates" {
    & py -3 $holdoutCandidates --gate-json "docs/final/artifacts/general_prophecy_explainability_holdout_gate_v1_latest.json" --output-json "docs/final/artifacts/general_prophecy_holdout_evolution_candidates_latest.json"
}

Invoke-Step "run_holdout_evolution_ablation" {
    & py -3 $holdoutAblation --gate-json "docs/final/artifacts/general_prophecy_explainability_holdout_gate_v1_latest.json" --candidates-json "docs/final/artifacts/general_prophecy_holdout_evolution_candidates_latest.json" --output-json "docs/final/artifacts/general_prophecy_holdout_evolution_ablation_latest.json"
}

# Alert is best-effort only; should not block daily refresh.
& py -3 $holdoutAlert --gate-json "docs/final/artifacts/general_prophecy_explainability_holdout_gate_v1_latest.json" --output-json "docs/final/artifacts/general_prophecy_explainability_holdout_alert_latest.json"
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARN: holdout alert dispatch step failed (non-blocking)." -ForegroundColor Yellow
}

Invoke-Step "build_myeongni_promotion_gate" {
    & py -3 $myeongniGate --weather-quality "docs/final/artifacts/general_prophecy_explainability_quality_v1_latest.json"
}

Invoke-Step "build_mkm_myeongni_response_v2" {
    & py -3 $mkmMyeongniV2 `
        --weather-quality-json "docs/final/artifacts/general_prophecy_explainability_quality_v1_latest.json" `
        --hold-confidence-cut $MyeongniHoldConfidenceCut `
        --reduce-direction-cut $MyeongniReduceDirectionCut `
        --reduce-confidence-cut $MyeongniReduceConfidenceCut `
        --output-json "docs/final/artifacts/mkm_myeongni_response_v2_latest.json"
}

Invoke-Step "validate_mkm_myeongni_response_v2" {
    & py -3 $mkmMyeongniV2Validate --response-json "docs/final/artifacts/mkm_myeongni_response_v2_latest.json"
}

if ($includeLogosV2Flag) {
    Invoke-Step "build_mkm_logos_response_v2" {
        & py -3 $mkmLogosV2 `
            --evidence-link $logosBriefPath `
            --evidence-link $notebookManifestPath `
            --output-json "docs/final/artifacts/mkm_logos_response_v2_latest.json"
    }

    Invoke-Step "validate_mkm_logos_response_v2" {
        & py -3 $mkmLogosV2Validate --response-json "docs/final/artifacts/mkm_logos_response_v2_latest.json"
    }
}

if ($enableLogosResponseV1RetryFlag) {
    Invoke-Step "build_logos_response_retry_inputs_v1" {
        & py -3 $logosResponseV1InputBuilder `
            --mkm-json "docs/final/artifacts/mkm_logos_response_v2_latest.json" `
            --output-raw $LogosResponseV1PrimaryInput `
            --output-retry $LogosResponseV1RetryInput `
            --raw-format "fenced"
    }

    Invoke-Step "run_logos_response_retry_pipeline_v1" {
        $retryArgs = @(
            "-3",
            $logosResponseV1Retry,
            "--input", $LogosResponseV1PrimaryInput,
            "--output-json", "docs/final/artifacts/logos_response_v1_retry_selected_latest.json",
            "--output-md", "docs/final/artifacts/logos_response_v1_retry_brief_latest.md",
            "--report-json", "docs/final/artifacts/logos_response_v1_retry_report_latest.json",
            "--max-attempts", $LogosResponseV1MaxAttempts
        )
        $retryAbs = Join-Path $WorkspaceRoot $LogosResponseV1RetryInput
        if (Test-Path -LiteralPath $retryAbs) {
            $retryArgs += @("--retry-input", $LogosResponseV1RetryInput)
        }
        & py @retryArgs
    }

    if ($enableLogosResponseQualityScoreFlag) {
        Invoke-Step "build_logos_response_quality_score_v1" {
            & py -3 $logosResponseQualityScore `
                --selected-json "docs/final/artifacts/logos_response_v1_retry_selected_latest.json" `
                --retry-report-json "docs/final/artifacts/logos_response_v1_retry_report_latest.json" `
                --brief-md "docs/final/artifacts/logos_response_v1_retry_brief_latest.md" `
                --output-json "docs/final/artifacts/logos_response_quality_score_v1_latest.json"
        }

        if ($enableLogosResponseQualityAlertFlag) {
            # Alert is best-effort only; should not block daily refresh.
            & py -3 $logosResponseQualityAlert `
                --score-json "docs/final/artifacts/logos_response_quality_score_v1_latest.json" `
                --output-json "docs/final/artifacts/logos_response_quality_score_alert_latest.json" `
                --overall-min $LogosResponseQualityMinOverall
            if ($LASTEXITCODE -ne 0) {
                Write-Host "WARN: logos quality alert dispatch step failed (non-blocking)." -ForegroundColor Yellow
            }
        }
    }
}

Write-Host "General prophecy daily queue refresh done."
