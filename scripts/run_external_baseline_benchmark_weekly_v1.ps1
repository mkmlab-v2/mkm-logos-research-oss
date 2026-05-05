<#
.SYNOPSIS
  Weekly B-track external baseline benchmark chain (manual-editorial baseline only).

.DESCRIPTION
  Runs:
  1) autofill core100 mapping (provisional)
  2) mapping quality gate
  3) overlap reports (global/core100 mapped/fullcanon)
  4) top-k sensitivity sweep
  5) comparison summary
#>
param(
    [string]$ExternalInput = "docs/final/artifacts/external_cross_references_openbible/cross_references.txt",
    [string]$Core100MapJson = "docs/final/artifacts/core100_node_ref_map_template_v1.json",
    [switch]$SkipAutofill
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

function Resolve-WorkspacePath([string]$PathStr) {
    if ([System.IO.Path]::IsPathRooted($PathStr)) { return $PathStr }
    return (Join-Path $workspaceRoot $PathStr)
}

Write-Host "[0/24] Validate required inputs exist" -ForegroundColor Cyan
$required = @(
    @{ Label = "OpenBible cross_references (manual-editorial baseline)"; Path = (Resolve-WorkspacePath $ExternalInput) },
    @{ Label = "core100 node-ref map JSON"; Path = (Resolve-WorkspacePath $Core100MapJson) },
    @{ Label = "global_atom_network_edges_latest.jsonl"; Path = (Join-Path $workspaceRoot "docs/final/artifacts/global_atom_network_edges_latest.jsonl") },
    @{ Label = "global_atom_network_core100_edges_latest.jsonl"; Path = (Join-Path $workspaceRoot "docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl") },
    @{ Label = "full_canon_edges.jsonl"; Path = (Join-Path $workspaceRoot "docs/final/artifacts/global_atom_full_canon/20260428T095207Z_full_canon_edges.jsonl") }
)
foreach ($item in $required) {
    if (-not (Test-Path -LiteralPath $item.Path)) {
        Write-Host "ERROR: Missing $($item.Label)" -ForegroundColor Red
        Write-Host "  Expected path: $($item.Path)" -ForegroundColor Red
        Write-Host "  OpenBible file is not in Git (large); copy cross_references.txt into docs/final/artifacts/external_cross_references_openbible/ or pass -ExternalInput." -ForegroundColor Yellow
        exit 1
    }
}

if (-not $SkipAutofill) {
    Write-Host "[1/24] Autofill core100 node map (provisional)" -ForegroundColor Cyan
    & py "scripts/autofill_core100_node_ref_map_from_openbible_v1.py" "--map-json" $Core100MapJson "--openbible-txt" $ExternalInput
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[2/24] Check core100 map quality gate" -ForegroundColor Cyan
& py "scripts/check_core100_node_ref_map_quality_v1.py" "--map-json" $Core100MapJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/24] Build core100 audit sample (50 + vote confidence)" -ForegroundColor Cyan
& py "scripts/build_core100_node_ref_audit_sample_v1.py" "--map-json" $Core100MapJson "--openbible-txt" $ExternalInput "--sample-size" "50"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/24] Build overlap reports (global/core100/fullcanon)" -ForegroundColor Cyan
& py "scripts/parse_external_baseline_v1.py" "--external-input" $ExternalInput "--internal-edges-jsonl" "docs/final/artifacts/global_atom_network_edges_latest.jsonl" "--report-out-json" "docs/final/artifacts/external_bible_crossref_openbible_overlap_report_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/parse_external_baseline_v1.py" "--external-input" $ExternalInput "--internal-edges-jsonl" "docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl" "--node-ref-map-json" $Core100MapJson "--top-k" "100" "--range-mode" "start" "--report-out-json" "docs/final/artifacts/external_bible_crossref_openbible_overlap_report_core100_mapped_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/parse_external_baseline_v1.py" "--external-input" $ExternalInput "--internal-edges-jsonl" "docs/final/artifacts/global_atom_full_canon/20260428T095207Z_full_canon_edges.jsonl" "--report-out-json" "docs/final/artifacts/external_bible_crossref_openbible_overlap_report_fullcanon_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/24] Sweep top-k sensitivity (start)" -ForegroundColor Cyan
& py "scripts/sweep_external_baseline_topk_v1.py" "--external-input" $ExternalInput "--internal-edges-jsonl" "docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl" "--node-ref-map-json" $Core100MapJson "--output-json" "docs/final/artifacts/external_bible_crossref_topk_sweep_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[6/24] Sweep top-k sensitivity (expand)" -ForegroundColor Cyan
& py "scripts/sweep_external_baseline_topk_v1.py" "--external-input" $ExternalInput "--internal-edges-jsonl" "docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl" "--node-ref-map-json" $Core100MapJson "--range-mode" "expand" "--output-json" "docs/final/artifacts/external_bible_crossref_topk_sweep_expand_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[7/24] Build range-mode A/B decision" -ForegroundColor Cyan
& py "scripts/build_external_baseline_range_mode_ab_decision_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[8/24] Build dual-mode report (operating+exploratory)" -ForegroundColor Cyan
& py "scripts/build_external_baseline_dual_mode_report_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[9/24] Build exploration signal brief (strong_delta only)" -ForegroundColor Cyan
& py "scripts/build_external_baseline_exploration_signal_brief_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$briefPath = "docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json"
if (Test-Path -LiteralPath $briefPath) {
    $brief = Get-Content -LiteralPath $briefPath -Raw | ConvertFrom-Json
    if ($brief.recommended_next_action -eq "enqueue_human_review_and_run_extended_sweep") {
        Write-Host "[10/24] Run extended exploratory sweep (triggered by strong_delta)" -ForegroundColor Yellow
        try {
            & py "scripts/run_external_baseline_extended_sweep_v1.py" "--external-input" $ExternalInput "--internal-edges-jsonl" "docs/final/artifacts/global_atom_network_core100_edges_latest.jsonl" "--node-ref-map-json" $Core100MapJson
            if ($LASTEXITCODE -ne 0) { throw "extended sweep exit code $LASTEXITCODE" }
            & py "scripts/build_external_baseline_extended_sweep_status_v1.py" "--status" "success" "--message" "extended sweep completed"
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        } catch {
            Write-Host "[10/24] Extended sweep failed; continue with fallback." -ForegroundColor DarkYellow
            & py "scripts/build_external_baseline_extended_sweep_status_v1.py" "--status" "failed" "--message" "extended sweep failed; fallback to baseline chain"
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        Write-Host "[11/24] Rebuild exploration brief with extended sweep evidence" -ForegroundColor Cyan
        & py "scripts/build_external_baseline_exploration_signal_brief_v1.py"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "[10/24] Skip extended exploratory sweep (no strong_delta trigger)" -ForegroundColor DarkGray
        & py "scripts/build_external_baseline_extended_sweep_status_v1.py" "--status" "skipped" "--message" "no strong_delta trigger"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "[11/24] Skip exploration brief rebuild (no extended sweep evidence update)" -ForegroundColor DarkGray
    }
}

Write-Host "[12/24] Build human review queue artifact" -ForegroundColor Cyan
& py "scripts/build_external_baseline_human_review_queue_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13/24] Build human review resolution artifact" -ForegroundColor Cyan
& py "scripts/build_external_baseline_human_review_resolution_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[14/24] Build threshold recalibration hint" -ForegroundColor Cyan
& py "scripts/build_external_baseline_threshold_recalibration_hint_v1.py" "--streak-trigger" "2"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[15/24] Build threshold tuning proposal (hint-driven)" -ForegroundColor Cyan
$hintPath = "docs/final/artifacts/external_bible_crossref_threshold_recalibration_hint_latest.json"
if (Test-Path -LiteralPath $hintPath) {
    $hint = Get-Content -LiteralPath $hintPath -Raw | ConvertFrom-Json
    if ($hint.hint_active -eq $true) {
        & py "scripts/build_external_baseline_threshold_tuning_proposal_v1.py"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "[15/24] Skip tuning proposal (hint not active)" -ForegroundColor DarkGray
    }
}

Write-Host "[16/24] Evaluate threshold apply gate" -ForegroundColor Cyan
& py "scripts/build_external_baseline_threshold_apply_gate_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$gatePath = "docs/final/artifacts/external_bible_crossref_threshold_apply_gate_latest.json"
if (Test-Path -LiteralPath $gatePath) {
    $gate = Get-Content -LiteralPath $gatePath -Raw | ConvertFrom-Json
    $approvalWarningPath = "docs/final/artifacts/external_bible_crossref_approval_expiry_warning_latest.json"
    $effectReportPath = "docs/final/artifacts/external_bible_crossref_threshold_effect_report_latest.json"
    $renewalDue = $false
    $effectChanged = $false
    if (Test-Path -LiteralPath $approvalWarningPath) {
        $approvalWarning = Get-Content -LiteralPath $approvalWarningPath -Raw | ConvertFrom-Json
        $renewalDue = [bool]$approvalWarning.renewal_due
    }
    if (Test-Path -LiteralPath $effectReportPath) {
        $effectReport = Get-Content -LiteralPath $effectReportPath -Raw | ConvertFrom-Json
        if ($effectReport.label_distribution_delta_vs_previous) {
            $d = $effectReport.label_distribution_delta_vs_previous
            $effectChanged = (([int]$d.promising -ne 0) -or ([int]$d.watch -ne 0) -or ([int]$d.below_watch -ne 0))
        }
    }
    $applyRecommended = ($renewalDue -or $effectChanged)
    if ($gate.can_apply_thresholds -eq $true) {
        if ($applyRecommended) {
            Write-Host "[16/24] Apply thresholds from approved proposal (policy: recommended)" -ForegroundColor Yellow
            & py "scripts/apply_external_baseline_thresholds_from_proposal_v1.py"
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        } else {
            Write-Host "[16/24] Skip threshold apply (policy: not recommended this cycle)" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "[16/24] Skip threshold apply (gate blocked)" -ForegroundColor DarkGray
    }
}

Write-Host "[17/24] Build comparison summary" -ForegroundColor Cyan
& py "scripts/build_external_baseline_overlap_comparison_v1.py" "--thresholds-json" "docs/final/artifacts/btrack_external_baseline_thresholds_v1.json" "--dual-mode-json" "docs/final/artifacts/external_bible_crossref_dual_mode_report_latest.json" "--exploration-brief-json" "docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_external_baseline_threshold_effect_report_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[18/24] Build latest artifact index" -ForegroundColor Cyan
& py "scripts/build_external_baseline_latest_index_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[19/24] Build apply-log summary and health check" -ForegroundColor Cyan
& py "scripts/build_external_baseline_threshold_apply_log_summary_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_external_baseline_health_check_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_external_baseline_health_alert_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_external_baseline_approval_expiry_warning_v1.py" "--warn-within-hours" "24"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_external_baseline_weekly_rollup_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_external_baseline_latest_index_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[20/24] Smoke tests (pytest: parser + chain integration)" -ForegroundColor Cyan
& py -m pytest "tests/test_parse_external_baseline_v1_smoke.py" "tests/test_external_baseline_chain_integration_smoke.py" -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[21/24] Chain complete." -ForegroundColor Green
Write-Host "[22/24] Health alert, approval warning, weekly rollup complete." -ForegroundColor Green
Write-Host "[23/24] Latest index refreshed with new artifacts." -ForegroundColor Green
Write-Host "[24/24] Done (manual-editorial baseline chain)." -ForegroundColor Green
exit 0
