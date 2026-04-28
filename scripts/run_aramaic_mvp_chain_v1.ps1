# Run Aramaic MVP B-track chain (extract -> normalize -> nodes -> edges -> semantic quality -> score -> weight sweep -> bridge coef apply -> score refresh -> shadow compare -> meaning graph -> insight candidates -> insight-reflected score/shadow).
param(
    [string]$InputJsonl = "data/logos/verse_decoded_v2.jsonl",
    [string]$CorpusOutJsonl = "reports/constitution/btrack_pilot/aramaic_core_corpus_v1.jsonl",
    [string]$NodesOutJsonl = "docs/final/artifacts/aramaic_graph_nodes_v1.jsonl",
    [string]$EdgesOutJsonl = "docs/final/artifacts/aramaic_graph_edges_v1.jsonl",
    [string]$BridgeNodesOutJsonl = "docs/final/artifacts/aramaic_cross_corpus_bridge_nodes_v1.jsonl",
    [string]$BridgeEdgesOutJsonl = "docs/final/artifacts/aramaic_cross_corpus_bridge_edges_v1.jsonl",
    [string]$BridgeCoefRecommendedJson = "docs/final/artifacts/aramaic_regime_shift_bridge_coef_recommended_latest.json",
    [string]$InsightCapThresholdSweepJson = "docs/final/artifacts/aramaic_insight_cap_bucket_threshold_sweep_latest.json",
    [string]$InsightCapThresholdRecommendedJson = "docs/final/artifacts/aramaic_insight_cap_bucket_threshold_recommended_latest.json",
    [string]$SemanticQualityOutJson = "docs/final/artifacts/aramaic_semantic_edge_quality_latest.json",
    [string]$ScoreOutJson = "docs/final/artifacts/aramaic_regime_shift_score_latest.json",
    [string]$MeaningGraphNodesOutJsonl = "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl",
    [string]$MeaningGraphEdgesOutJsonl = "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl",
    [string]$MeaningInsightOutJson = "docs/final/artifacts/bible_meaning_insight_candidates_latest.json",
    [string]$SymbolicTopologyInsightOutJson = "docs/final/artifacts/symbolic_topology_insight_latest.json",
    [string]$SymbolAtomMappingOutJson = "docs/final/artifacts/symbol_atom_mapping_latest.json",
    [string]$AtomResonanceOutJson = "docs/final/artifacts/atom_resonance_report_latest.json",
    [string]$ScholarlySymbolBridgeOutJson = "docs/final/artifacts/scholarly_symbol_bridge_latest.json",
    [string]$Gematria4dCouplingOutJson = "docs/final/artifacts/gematria_4d_coupling_latest.json",
    [string]$Gematria4dAblationOutJson = "docs/final/artifacts/gematria_4d_ablation_latest.json",
    [string]$MultiSymbolResonance4dOutJson = "docs/final/artifacts/multi_symbol_resonance_4d_latest.json",
    [string]$MultiSymbolCandidateSelectorOutJson = "docs/final/artifacts/multi_symbol_candidate_selector_latest.json",
    [string]$SurvivorEvalOutJson = "docs/final/artifacts/insight_survivor_eval_latest.json",
    [string]$SurvivorCandidatesOutJson = "docs/final/artifacts/insight_survivor_candidates_latest.json",
    [string]$KnowledgeIpReportOutJson = "docs/final/artifacts/bible_meaning_knowledge_ip_report_latest.json",
    [string]$KnowledgeIpVizOutJson = "docs/final/artifacts/bible_meaning_knowledge_ip_viz_latest.json",
    [string]$SurvivorHealthAlertOutJson = "docs/final/artifacts/insight_survivor_health_alert_latest.json",
    [string]$TwoTrackFusionReportOutJson = "docs/final/artifacts/two_track_fusion_report_latest.json",
    [string]$TwoTrackFusionBriefOutJson = "docs/final/artifacts/two_track_fusion_brief_latest.json",
    [string]$TwoTrackFusionPresentationBriefOutJson = "docs/final/artifacts/two_track_fusion_presentation_brief_latest.json",
    [string]$TwoTrackPresentationCopydeckOutJson = "docs/final/artifacts/two_track_presentation_copydeck_latest.json",
    [string]$TwoTrackPresentationAudiencePackOutJson = "docs/final/artifacts/two_track_presentation_audience_pack_latest.json",
    [string]$TwoTrackPresenterNotesOutJson = "docs/final/artifacts/two_track_presenter_notes_latest.json",
    [string]$TwoTrackQaPackOutJson = "docs/final/artifacts/two_track_qa_pack_latest.json",
    [string]$TwoTrackAcademicPacketOutJson = "docs/final/artifacts/two_track_academic_submission_packet_latest.json",
    [string]$TwoTrackFalsificationSuiteOutJson = "docs/final/artifacts/two_track_falsification_suite_latest.json",
    [string]$TwoTrackFailBoundaryReportOutJson = "docs/final/artifacts/two_track_falsification_boundary_report_latest.json",
    [string]$TwoTrackFailBoundaryGateOutJson = "docs/final/artifacts/two_track_fail_boundary_gate_latest.json",
    [string]$TwoTrackBenchmarkComparisonOutJson = "docs/final/artifacts/two_track_benchmark_comparison_latest.json",
    [string]$TwoTrackSignificanceReportOutJson = "docs/final/artifacts/two_track_statistical_significance_report_latest.json",
    [string]$TwoTrackSignificanceBaselineTuningJson = "docs/final/artifacts/two_track_significance_baseline_tuning_v1.json",
    [string]$TwoTrackRawOosSamplesOutJsonl = "docs/final/artifacts/two_track_raw_oos_samples_latest.jsonl",
    [string]$TwoTrackRawOosReadinessOutJson = "docs/final/artifacts/two_track_raw_oos_readiness_latest.json",
    [string]$TwoTrackPublicSafeReportOutJson = "docs/final/artifacts/two_track_public_safe_report_latest.json",
    [string]$TwoTrackSubmissionEvidenceBundleOutJson = "docs/final/artifacts/two_track_submission_evidence_bundle_latest.json",
    [string]$TwoTrackSubmissionDraftOutJson = "docs/final/artifacts/two_track_submission_draft_latest.json",
    [string]$TwoTrackSubmissionCameraReadyOutJson = "docs/final/artifacts/two_track_submission_camera_ready_latest.json"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

Write-Host "[1/5] Extract Aramaic core corpus" -ForegroundColor Cyan
& py "scripts/extract_aramaic_core_corpus_v1.py" "--input-jsonl" $InputJsonl "--output-jsonl" $CorpusOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/5] Normalize tokens" -ForegroundColor Cyan
& py "scripts/normalize_aramaic_tokens_v1.py" "--input-jsonl" $CorpusOutJsonl "--output-jsonl" $CorpusOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/5] Build graph nodes" -ForegroundColor Cyan
& py "scripts/build_aramaic_graph_nodes_v1.py" "--input-jsonl" $CorpusOutJsonl "--output-jsonl" $NodesOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/5] Build graph edges" -ForegroundColor Cyan
& py "scripts/build_aramaic_graph_edges_v1.py" "--input-jsonl" $NodesOutJsonl "--output-jsonl" $EdgesOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[5/9] Build cross-corpus bridge nodes/edges" -ForegroundColor Cyan
& py "scripts/build_aramaic_cross_corpus_bridge_v1.py" "--aramaic-nodes-jsonl" $NodesOutJsonl "--output-nodes-jsonl" $BridgeNodesOutJsonl "--output-edges-jsonl" $BridgeEdgesOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[6/9] Report semantic edge quality" -ForegroundColor Cyan
& py "scripts/report_aramaic_semantic_edge_quality_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges" "--output-json" $SemanticQualityOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[7/9] Score regime shift" -ForegroundColor Cyan
& py "scripts/score_aramaic_regime_shift_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges" "--output-json" $ScoreOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[8/10] Sweep score weights" -ForegroundColor Cyan
& py "scripts/run_aramaic_regime_shift_weight_sweep_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[9/10] Apply recommended bridge coefficients" -ForegroundColor Cyan
& py "scripts/apply_aramaic_regime_shift_bridge_coef_recommendation_v1.py" "--output-json" $BridgeCoefRecommendedJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[10/13] Build baseline vs best-weight shadow compare + refresh score_latest" -ForegroundColor Cyan
& py "scripts/score_aramaic_regime_shift_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges" "--bridge-lang-coef-json" $BridgeCoefRecommendedJson "--output-json" $ScoreOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/run_aramaic_regime_shift_shadow_compare_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[11/13] Build verse-theme-regime meaning graph" -ForegroundColor Cyan
& py "scripts/build_bible_meaning_graph_v1.py" "--verse-nodes-jsonl" $NodesOutJsonl "--bridge-nodes-jsonl" $BridgeNodesOutJsonl "--verse-edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--output-nodes-jsonl" $MeaningGraphNodesOutJsonl "--output-edges-jsonl" $MeaningGraphEdgesOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[12/13] Extract meaning insight candidates" -ForegroundColor Cyan
& py "scripts/extract_bible_meaning_insight_candidates_v1.py" "--nodes-jsonl" $MeaningGraphNodesOutJsonl "--edges-jsonl" $MeaningGraphEdgesOutJsonl "--output-json" $MeaningInsightOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13/15] Build survivor eval + select survivors" -ForegroundColor Cyan
& py "scripts/build_insight_survivor_eval_v1.py" "--insight-json" $MeaningInsightOutJson "--output-json" $SurvivorEvalOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/select_insight_survivor_candidates_v1.py" "--eval-json" $SurvivorEvalOutJson "--output-json" $SurvivorCandidatesOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13b/15] Build symbolic topology insight (Tree of Knowledge)" -ForegroundColor Cyan
& py "scripts/build_symbolic_topology_insight_v1.py" "--seed-symbol" "tree_of_knowledge_good_evil" "--meaning-json" $MeaningInsightOutJson "--survivor-json" $SurvivorCandidatesOutJson "--output-json" $SymbolicTopologyInsightOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13c/15] Build symbol-atom mapping + atom resonance" -ForegroundColor Cyan
& py "scripts/build_symbol_atom_mapping_v1.py" "--registry-json" "docs/final/artifacts/atom_anchor_registry_v1.json" "--symbolic-json" $SymbolicTopologyInsightOutJson "--output-json" $SymbolAtomMappingOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_atom_resonance_report_v1.py" "--mapping-json" $SymbolAtomMappingOutJson "--survivor-json" $SurvivorCandidatesOutJson "--output-json" $AtomResonanceOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13d/15] Build scholarly symbol bridge" -ForegroundColor Cyan
& py "scripts/build_scholarly_symbol_bridge_v1.py" "--mapping-json" $SymbolAtomMappingOutJson "--resonance-json" $AtomResonanceOutJson "--output-json" $ScholarlySymbolBridgeOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13e/15] Build 4D gematria coupling + ablation" -ForegroundColor Cyan
& py "scripts/build_gematria_4d_coupling_v1.py" "--symbolic-json" $SymbolicTopologyInsightOutJson "--bridge-json" $ScholarlySymbolBridgeOutJson "--output-json" $Gematria4dCouplingOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_gematria_4d_ablation_v1.py" "--coupling-json" $Gematria4dCouplingOutJson "--resonance-json" $AtomResonanceOutJson "--output-json" $Gematria4dAblationOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[13f/15] Build multi-symbol resonance + 4D ranking" -ForegroundColor Cyan
& py "scripts/build_multi_symbol_resonance_4d_v1.py" "--registry-json" "docs/final/artifacts/atom_anchor_registry_v1.json" "--survivor-json" $SurvivorCandidatesOutJson "--output-json" $MultiSymbolResonance4dOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/build_multi_symbol_candidate_selector_v1.py" "--multi-symbol-json" $MultiSymbolResonance4dOutJson "--output-json" $MultiSymbolCandidateSelectorOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[14/15] Re-score + shadow compare with insight signal" -ForegroundColor Cyan
& py "scripts/sweep_aramaic_insight_cap_bucket_thresholds_v1.py" "--output-json" $InsightCapThresholdSweepJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/apply_aramaic_insight_cap_bucket_threshold_recommendation_v1.py" "--sweep-json" $InsightCapThresholdSweepJson "--output-json" $InsightCapThresholdRecommendedJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$capDoc = Get-Content -LiteralPath $InsightCapThresholdRecommendedJson -Raw | ConvertFrom-Json
$rec = $capDoc.recommended
$midVol = [double]$rec.mid_vol_threshold
$highVol = [double]$rec.high_vol_threshold
$lowCap = [double]$rec.insight_max_delta_low_vol
$midCap = [double]$rec.insight_max_delta_mid_vol
$highCap = [double]$rec.insight_max_delta_high_vol

& py "scripts/score_aramaic_regime_shift_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges" "--bridge-lang-coef-json" $BridgeCoefRecommendedJson "--insight-json" $MeaningInsightOutJson "--survivor-json" $SurvivorCandidatesOutJson "--include-insight-signal" "--mid-vol-threshold" $midVol "--high-vol-threshold" $highVol "--insight-max-delta-low-vol" $lowCap "--insight-max-delta-mid-vol" $midCap "--insight-max-delta-high-vol" $highCap "--output-json" $ScoreOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/run_aramaic_regime_shift_shadow_compare_v1.py" "--edges-jsonl" $EdgesOutJsonl "--bridge-edges-jsonl" $BridgeEdgesOutJsonl "--include-bridge-edges" "--insight-json" $MeaningInsightOutJson "--survivor-json" $SurvivorCandidatesOutJson "--include-insight-signal" "--mid-vol-threshold" $midVol "--high-vol-threshold" $highVol "--insight-max-delta-low-vol" $lowCap "--insight-max-delta-mid-vol" $midCap "--insight-max-delta-high-vol" $highCap
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[15/17] Append insight cap threshold history" -ForegroundColor Cyan
& py "scripts/report_aramaic_insight_cap_threshold_history_v1.py" "--recommended-json" $InsightCapThresholdRecommendedJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[16/17] Evaluate insight cap threshold drift alert" -ForegroundColor Cyan
& py "scripts/alert_aramaic_insight_cap_threshold_drift_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[17/17] Survivor summary checkpoint" -ForegroundColor Cyan
Write-Host $SurvivorCandidatesOutJson

Write-Host "[18/20] Build Track-K knowledge IP report + viz payload" -ForegroundColor Cyan
& py "scripts/build_bible_meaning_knowledge_ip_report_v1.py" "--insight-json" $MeaningInsightOutJson "--survivor-json" $SurvivorCandidatesOutJson "--report-json" $KnowledgeIpReportOutJson "--viz-json" $KnowledgeIpVizOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[19/20] Evaluate Track-T survivor health alert" -ForegroundColor Cyan
& py "scripts/alert_insight_survivor_health_v1.py" "--survivor-json" $SurvivorCandidatesOutJson "--output-json" $SurvivorHealthAlertOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[20/20] Build two-track fusion report" -ForegroundColor Cyan
& py "scripts/build_two_track_fusion_report_v1.py" "--knowledge-report-json" $KnowledgeIpReportOutJson "--regime-score-json" $ScoreOutJson "--survivor-json" $SurvivorCandidatesOutJson "--survivor-alert-json" $SurvivorHealthAlertOutJson "--output-json" $TwoTrackFusionReportOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[21/21] Build human dashboard brief from two-track fusion" -ForegroundColor Cyan
& py "scripts/build_two_track_fusion_brief_v1.py" "--fusion-report-json" $TwoTrackFusionReportOutJson "--output-json" $TwoTrackFusionBriefOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[22/22] Build presentation-ready IP brief" -ForegroundColor Cyan
& py "scripts/build_two_track_fusion_presentation_brief_v1.py" "--brief-json" $TwoTrackFusionBriefOutJson "--output-json" $TwoTrackFusionPresentationBriefOutJson "--tone" "executive"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[23/23] Build slide copydeck (1-page + 3-page)" -ForegroundColor Cyan
& py "scripts/build_two_track_presentation_copydeck_v1.py" "--presentation-brief-json" $TwoTrackFusionPresentationBriefOutJson "--output-json" $TwoTrackPresentationCopydeckOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[24/24] Build audience variants (investor/policy/technical)" -ForegroundColor Cyan
& py "scripts/build_two_track_presentation_audience_pack_v1.py" "--copydeck-json" $TwoTrackPresentationCopydeckOutJson "--output-json" $TwoTrackPresentationAudiencePackOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[25/25] Build presenter notes (60s/180s)" -ForegroundColor Cyan
& py "scripts/build_two_track_presenter_notes_v1.py" "--audience-pack-json" $TwoTrackPresentationAudiencePackOutJson "--output-json" $TwoTrackPresenterNotesOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[26/26] Build audience Q&A pack (5x3)" -ForegroundColor Cyan
& py "scripts/build_two_track_qa_pack_v1.py" "--presenter-notes-json" $TwoTrackPresenterNotesOutJson "--output-json" $TwoTrackQaPackOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[27/27] Build academic submission packet (minimal)" -ForegroundColor Cyan
& py "scripts/build_two_track_academic_submission_packet_v1.py" "--score-json" $ScoreOutJson "--survivor-json" $SurvivorCandidatesOutJson "--qa-json" $TwoTrackQaPackOutJson "--output-json" $TwoTrackAcademicPacketOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[28/37] Run falsification suite (minimal)" -ForegroundColor Cyan
& py "scripts/run_two_track_falsification_suite_v1.py" "--academic-packet-json" $TwoTrackAcademicPacketOutJson "--qa-json" $TwoTrackQaPackOutJson "--output-json" $TwoTrackFalsificationSuiteOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[28b/37] Build falsification fail-boundary report + gate" -ForegroundColor Cyan
& py "scripts/build_two_track_falsification_boundary_report_v1.py" "--output-json" $TwoTrackFailBoundaryReportOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/alert_two_track_fail_boundary_gate_v1.py" "--boundary-json" $TwoTrackFailBoundaryReportOutJson "--survivor-json" $SurvivorCandidatesOutJson "--output-json" $TwoTrackFailBoundaryGateOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& py "scripts/enrich_two_track_qa_with_symbol_evidence_v1.py" "--qa-json" $TwoTrackQaPackOutJson "--selector-json" $MultiSymbolCandidateSelectorOutJson "--fail-boundary-gate-json" $TwoTrackFailBoundaryGateOutJson "--output-json" $TwoTrackQaPackOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[29/37] Build benchmark comparison" -ForegroundColor Cyan
& py "scripts/build_two_track_benchmark_comparison_v1.py" "--score-json" $ScoreOutJson "--survivor-json" $SurvivorCandidatesOutJson "--output-json" $TwoTrackBenchmarkComparisonOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[30/37] Build raw OOS sample scaffold" -ForegroundColor Cyan
& py "scripts/build_two_track_raw_oos_samples_seed_v1.py" "--benchmark-json" $TwoTrackBenchmarkComparisonOutJson "--output-jsonl" $TwoTrackRawOosSamplesOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[31/37] Ingest observed audit into raw OOS" -ForegroundColor Cyan
& py "scripts/ingest_two_track_raw_oos_from_audit_v1.py" "--input-jsonl" $TwoTrackRawOosSamplesOutJsonl "--output-jsonl" $TwoTrackRawOosSamplesOutJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[32/37] Build statistical significance report" -ForegroundColor Cyan
& py "scripts/build_two_track_statistical_significance_report_v1.py" "--benchmark-json" $TwoTrackBenchmarkComparisonOutJson "--baseline-tuning-json" $TwoTrackSignificanceBaselineTuningJson "--raw-oos-jsonl" $TwoTrackRawOosSamplesOutJsonl "--output-json" $TwoTrackSignificanceReportOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[33/37] Report raw OOS readiness" -ForegroundColor Cyan
& py "scripts/report_two_track_raw_oos_readiness_v1.py" "--raw-oos-jsonl" $TwoTrackRawOosSamplesOutJsonl "--benchmark-json" $TwoTrackBenchmarkComparisonOutJson "--output-json" $TwoTrackRawOosReadinessOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[34/37] Build public-safe report (redacted)" -ForegroundColor Cyan
& py "scripts/build_two_track_public_safe_report_v1.py" "--academic-json" $TwoTrackAcademicPacketOutJson "--benchmark-json" $TwoTrackBenchmarkComparisonOutJson "--significance-json" $TwoTrackSignificanceReportOutJson "--output-json" $TwoTrackPublicSafeReportOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[35/37] Build submission evidence bundle checklist" -ForegroundColor Cyan
& py "scripts/build_two_track_submission_evidence_bundle_v1.py" "--out" $TwoTrackSubmissionEvidenceBundleOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[36/37] Build submission draft (abstract + outline)" -ForegroundColor Cyan
& py "scripts/build_two_track_submission_draft_v1.py" "--output-json" $TwoTrackSubmissionDraftOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[37/37] Build camera-ready submission JSON" -ForegroundColor Cyan
& py "scripts/build_two_track_submission_camera_ready_v1.py" "--draft-json" $TwoTrackSubmissionDraftOutJson "--output-json" $TwoTrackSubmissionCameraReadyOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: Aramaic MVP chain completed." -ForegroundColor Green
