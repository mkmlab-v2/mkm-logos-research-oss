param(
    [string]$WorkflowName = "Dual Regime Integrity (Fact-Lock)",
    [int]$Limit = 10,
    [switch]$WatchLatest,
    [switch]$ShowFailedLog,
    [switch]$RunNumericNearMissGateCheck,
    [switch]$ApproveNumericNearMiss
)

$ErrorActionPreference = "Stop"

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

Write-Section "Recent workflow runs"
gh run list --workflow $WorkflowName --limit $Limit

Write-Section "Required tracked inputs"
git ls-files `
  "data/logos/manuscripts/apocrypha_std.jsonl" `
  "data/logos/manuscripts/dss_parsed.jsonl" `
  "data/logos/verse_decoded_v2.jsonl" `
  "data/logos/verse_distilled_11_1.jsonl"

Write-Section "Required tracked gate templates"
git ls-files `
  "data/logos/btrack_pilot/gates/symbol_lane_gate_template.json" `
  "data/logos/btrack_pilot/gates/promotion_gate_template.json" `
  "data/logos/btrack_pilot/gates/promotion_gate_candidate_subset.json"

Write-Section "Workflow chain/version check"
Select-String `
  -Path ".github/workflows/dual-regime-integrity.yml" `
  -Pattern "run_btrack_symbol_lane_gate_and_lock.py|actions/checkout@|actions/setup-python@|actions/upload-artifact@"

$runId = gh run list --workflow $WorkflowName --limit 1 --json databaseId --jq ".[0].databaseId"
if ([string]::IsNullOrWhiteSpace($runId)) {
    throw "Could not resolve latest run id for workflow: $WorkflowName"
}

Write-Section "Latest run"
gh run view $runId --json status,conclusion,url,workflowName,displayTitle

if ($RunNumericNearMissGateCheck) {
    $gateScript = "scripts/ops/run_numeric_near_miss_gate_check.ps1"
    if (-not (Test-Path -LiteralPath $gateScript)) {
        throw "Numeric near-miss gate script not found: $gateScript"
    }
    Write-Section "Numeric near-miss gate check"
    if ($ApproveNumericNearMiss) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $gateScript -ApproveNumericNearMiss
    }
    else {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $gateScript
    }
}

if ($WatchLatest) {
    Write-Section "Watch latest run"
    gh run watch $runId --interval 5 --exit-status
}

if ($ShowFailedLog) {
    Write-Section "Failed log (if any)"
    gh run view $runId --log-failed
}

Write-Host ""
Write-Host "OK: CI healthcheck finished (run_id=$runId)" -ForegroundColor Green
