# One-shot ops chain (local): Multitarget pre-gate -> P0 Fact-Lock bundle -> Sasang JSONL validate -> BTC Multilens smoke -> contract pytest subset.
# Optional: -IncludeP1AB (Multilens P1 A/B + final selection after core Fact-Lock).
# Optional: -IncludeJemaaiCloudChecks (verify jemaai.cloud MVP paths + nginx example; no VPS deploy).
# Optional: -SkipMultitargetPreGate (skip multitarget topology/trainability pre-gate).
# No live trading. Network required for step 3 (Binance + FGI).
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_workspace_autopilot_chain.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\workspace\scripts\run_workspace_autopilot_chain.ps1 -IncludeP1AB -IncludeJemaaiCloudChecks

param(
    [switch]$IncludeP1AB,
    [switch]$IncludeJemaaiCloudChecks,
    [switch]$IncludeJemaaiE2ESmoke,
    [switch]$SkipMultitargetPreGate,
    [bool]$TreatMultitargetHoldAsSuccess = $true
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

$maint = [System.Environment]::GetEnvironmentVariable("MKM_WORKSPACE_MAINTENANCE")
if ($maint -and ($maint.Trim().ToLower() -in @("1", "true", "yes", "on"))) {
    Write-Host "SKIP: MKM_WORKSPACE_MAINTENANCE active (autopilot chain not run)" -ForegroundColor Yellow
    exit 0
}

if (-not $SkipMultitargetPreGate) {
    $topologyScript = Join-Path $workspaceRoot "scripts\build_multitarget_label_topology_report_v1.py"
    $trainabilityGateScript = Join-Path $workspaceRoot "scripts\eval_target_conditioned_trainability_gate_v1.py"
    $topologyJson = Join-Path $workspaceRoot "artifacts\B_track\kaggle_training_5seed\multitarget_classification\multitarget_label_topology_report_latest.json"
    $trainabilityJson = Join-Path $workspaceRoot "artifacts\B_track\kaggle_training_5seed\multitarget_classification\target_conditioned_trainability_gate_latest.json"
    $unseenTcJson = Join-Path $workspaceRoot "artifacts\B_track\kaggle_training_5seed\multitarget_classification\target_conditioned_benchmark_summary_unseen_target.json"
    $seenTcJson = Join-Path $workspaceRoot "artifacts\B_track\kaggle_training_5seed\multitarget_classification\target_conditioned_benchmark_summary_seen_label.json"

    foreach ($p in @($topologyScript, $trainabilityGateScript, $unseenTcJson, $seenTcJson)) {
        if (-not (Test-Path -LiteralPath $p)) {
            throw "Multitarget pre-gate missing required file: $p"
        }
    }

    Write-Host "=== [0/4] multitarget topology + trainability pre-gate ===" -ForegroundColor Cyan
    & py $topologyScript --source-csv (Join-Path $workspaceRoot "data\kaggle\processed\multitarget_bioactivity\normalized.csv") --output-json $topologyJson
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & py $trainabilityGateScript --unseen-benchmark-json $unseenTcJson --seen-label-benchmark-json $seenTcJson --label-topology-json $topologyJson --output-json $trainabilityJson
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $gate = Get-Content -LiteralPath $trainabilityJson -Raw | ConvertFrom-Json
    if ($null -ne $gate -and "$($gate.final_status)".ToUpper() -eq "HOLD") {
        Write-Host "PRE-GATE HOLD: multitarget trainability gate blocked downstream heavy chain." -ForegroundColor Yellow
        if ($TreatMultitargetHoldAsSuccess) {
            Write-Host "Exit policy: HOLD treated as successful stop (exit 0)." -ForegroundColor Yellow
            exit 0
        }
        Write-Host "Exit policy: HOLD treated as failure (exit 20)." -ForegroundColor Red
        exit 20
    }
}

$flArgs = @()
if ($IncludeP1AB) {
    $flArgs += "-IncludeP1AB"
}

Write-Host "=== [1/4] run_fact_lock_bundle.ps1 $(if ($IncludeP1AB) { '(+P1 A/B)' }) ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $workspaceRoot "scripts\run_fact_lock_bundle.ps1") @flArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [2/4] sasang validate-sample (sample + btc_anchor) ===" -ForegroundColor Cyan
& py (Join-Path $workspaceRoot "scripts\sasang_dynamics_regime_mapping_ledger.py") @("validate-sample")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py (Join-Path $workspaceRoot "scripts\sasang_dynamics_regime_mapping_ledger.py") @(
    "validate-sample", "--path", (Join-Path $workspaceRoot "data\sasang\sasang_dynamics_regime_mapping_v1.btc_anchor_smoke.jsonl")
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [3/4] run_btc_anchor_multilens_smoke.ps1 ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $workspaceRoot "scripts\run_btc_anchor_multilens_smoke.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== [4/4] pytest (sasang ledger + multilens thin + kospi dynamics bridge/verify smoke) ===" -ForegroundColor Cyan
& py -m pytest @(
    (Join-Path $workspaceRoot "tests\test_sasang_dynamics_regime_mapping_ledger.py"),
    (Join-Path $workspaceRoot "tests\test_multilens_eval_harness_v2_thin.py"),
    (Join-Path $workspaceRoot "tests\test_kospi_sasang_dynamics_bridge_v1.py"),
    (Join-Path $workspaceRoot "tests\test_verify_kospi_sasang_dynamics_holdout_smoke.py"),
    "-q", "--tb=short"
)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeJemaaiCloudChecks) {
    Write-Host "=== [5] jemaai.cloud MVP path checks (no deploy) ===" -ForegroundColor Cyan
    $mvp = Join-Path $workspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp"
    $check = @(
        (Join-Path $mvp "JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md"),
        (Join-Path $mvp "public_event_gateway.py"),
        (Join-Path $mvp "nginx_public_event_gateway.conf.example"),
        (Join-Path $mvp "examples\public_event_ingest_minimal.v1.json"),
        (Join-Path $mvp "public_showroom_poll.html"),
        (Join-Path $mvp "compression_v2_explorer.html"),
        (Join-Path $workspaceRoot "scripts\Serve-CompressionV2Explorer.ps1"),
        (Join-Path $workspaceRoot "scripts\Start-CompressionV2ExplorerDemo.ps1"),
        (Join-Path $workspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\ensure_public_event_gateway.ps1"),
        (Join-Path $workspaceRoot "scripts\print_gemini_env_hygiene_hint.ps1")
    )
    foreach ($p in $check) {
        if (-not (Test-Path -LiteralPath $p)) {
            throw "jemaai.cloud readiness: missing $p"
        }
        Write-Host "  OK: $p" -ForegroundColor DarkGray
    }
    Write-Host "jemaai.cloud: deploy nginx `location` from nginx_public_event_gateway.conf.example; run ensure_public_event_gateway.ps1 on host; set PUBLIC_EVENT_GATEWAY_TOKEN. See JEMAAI_CLOUD_PUBLIC_SHOWROOM_SPEC.md." -ForegroundColor Green
}

if ($IncludeJemaaiE2ESmoke) {
    Write-Host "=== [6] jemaai.cloud public-event E2E smoke ===" -ForegroundColor Cyan
    $smokeScript = Join-Path $workspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\run_jemaai_public_event_e2e_smoke.ps1"
    if (-not (Test-Path -LiteralPath $smokeScript)) {
        throw "jemaai.cloud E2E smoke: missing $smokeScript"
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $smokeScript -ApiBaseUrl "https://api.jemaai.cloud"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== autopilot chain OK ===" -ForegroundColor Green
exit 0
