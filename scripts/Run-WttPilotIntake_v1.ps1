# WTT masked session JSONL -> validate + bootstrap + FSM batch (compression ROI chain separate; SEND HOLD).
param(
    [Parameter(Mandatory = $true)]
    [string]$TenantId,
    [Parameter(Mandatory = $true)]
    [string]$SessionJsonl,
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MaxSessions = 30,
    [int]$MinSessions = 20,
    [switch]$AllowSynthetic,
    [switch]$AllowStubTemplate,
    [switch]$AllowOperatorPanel,
    [switch]$SkipFsmBatch,
    [switch]$RunPolicyTune,
    [switch]$PromoteTunedPolicy,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$SessionPath = if ([System.IO.Path]::IsPathRooted($SessionJsonl)) {
    (Resolve-Path -LiteralPath $SessionJsonl).Path
} else {
    (Resolve-Path -LiteralPath (Join-Path $WorkspaceRoot $SessionJsonl)).Path
}

if (-not (Test-Path -LiteralPath $SessionPath)) {
    Write-Error "Session JSONL not found: $SessionPath"
}

$rowCount = (Get-Content -LiteralPath $SessionPath | Where-Object { $_.Trim() -ne "" }).Count
if ($rowCount -lt $MinSessions) {
    Write-Error "Session JSONL has $rowCount rows; need at least $MinSessions (max $MaxSessions)."
}

$laneCount = @($AllowSynthetic, $AllowStubTemplate, $AllowOperatorPanel | Where-Object { $_ }).Count
if ($laneCount -gt 1) {
    Write-Error "Use only one of -AllowSynthetic, -AllowStubTemplate, -AllowOperatorPanel."
}
$customerMasked = (-not $AllowSynthetic) -and (-not $AllowStubTemplate) -and (-not $AllowOperatorPanel)
$stubTemplate = $AllowStubTemplate
$operatorPanel = $AllowOperatorPanel
$validateOut = Join-Path $WorkspaceRoot "reports/wtt_pilot_jsonl_validate_v1_latest.json"
# Per-tenant FSM by default — only synthetic-spicy dev lane updates global spicy SSOT.
if ($AllowSynthetic) {
    $fsmOut = Join-Path $WorkspaceRoot "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json"
} else {
    $fsmOut = Join-Path $WorkspaceRoot "reports/wtt_tenant_fsm_batch_${TenantId}_v1_latest.json"
}
$manifestOut = Join-Path $WorkspaceRoot "reports/wtt_pilot_intake_${TenantId}_v1.json"

Write-Host "=== WTT pilot intake (session JSONL) ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | sessions: $rowCount | customer_masked: $customerMasked | stub_template: $stubTemplate | operator_panel: $operatorPanel | SEND_GATE HOLD" -ForegroundColor Yellow
Write-Host "kit: docs/final/artifacts/wtt_pilot_target_intake_kit_v1_latest.json" -ForegroundColor DarkGray

if ($DryRun) {
    Write-Host "[DryRun] validate -> bootstrap -> fsm batch" -ForegroundColor DarkGray
    exit 0
}

Write-Host "=== Step 1/3: validate JSONL + PII scan ===" -ForegroundColor Cyan
$validateArgs = @(
    "scripts/validate_wtt_pilot_jsonl_v1.py",
    "--jsonl", $SessionPath,
    "--out", $validateOut,
    "--min-sessions", "$MinSessions",
    "--max-sessions", "$MaxSessions",
    "--strict"
)
if ($AllowSynthetic -or $customerMasked) {
    $validateArgs += "--allow-missing-synthetic-labels"
}
if ($AllowOperatorPanel) {
    $validateArgs += "--lane-operator-panel"
    if ($MinSessions -lt 30) { $MinSessions = 30 }
}
& py @validateArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 2/3: bootstrap tenant corpus + manifest ===" -ForegroundColor Cyan
$bootstrapArgs = @(
    "scripts/bootstrap_wtt_pilot_intake_v1.py",
    "--tenant-id", $TenantId,
    "--source-jsonl", $SessionPath,
    "--max-sessions", "$MaxSessions",
    "--validate-report", $validateOut
)
if ($stubTemplate) {
    $bootstrapArgs += "--stub-template"
} elseif ($operatorPanel) {
    $bootstrapArgs += "--operator-panel"
} elseif ($customerMasked) {
    $bootstrapArgs += "--customer-masked"
}
& py @bootstrapArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipFsmBatch) {
    Write-Host "=== Step 3/3: FSM batch on bootstrapped corpus ===" -ForegroundColor Cyan
    $corpusCopy = Join-Path $WorkspaceRoot "data/wtt/intake/wtt_pilot_${TenantId}_v1.jsonl"
    & py scripts/run_wtt_spicy_corpus_fsm_batch_v1.py --jsonl $corpusCopy --out $fsmOut
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & py scripts/bootstrap_wtt_pilot_intake_v1.py `
        --tenant-id $TenantId `
        --source-jsonl $SessionPath `
        --max-sessions $MaxSessions `
        --validate-report $validateOut `
        --fsm-batch-report $fsmOut `
        @($(if ($stubTemplate) { "--stub-template" } elseif ($operatorPanel) { "--operator-panel" } elseif ($customerMasked) { "--customer-masked" }))
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($RunPolicyTune) {
    Write-Host "=== Optional: FSM policy tune from corpus ===" -ForegroundColor Cyan
    $tuneArgs = @(
        "scripts/tune_wtt_dialog_risk_policy_from_corpus_v1.py",
        "--jsonl", $SessionPath
    )
    if ($PromoteTunedPolicy) { $tuneArgs += "--promote" }
    & py @tuneArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "OK manifest: $manifestOut" -ForegroundColor Green
exit 0
