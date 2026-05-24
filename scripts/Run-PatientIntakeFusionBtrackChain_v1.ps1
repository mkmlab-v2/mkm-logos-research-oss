# Patient intake fusion B-track chain: harvest (optional) → lens pack → intake bundle + rationale.
param(
    [string]$IntakeJson = "tests/fixtures/patient_intake_soeum_clinical_v1.example.json",
    [switch]$ApplyIjeomaHarvest,
    [switch]$HarvestDryRunOnly,
    [switch]$IncludeTrackCDashboard,
    [switch]$PruneIjeomaHarvestLexicon,
    [switch]$IncludeShowroomTrustSlice,
    [switch]$MirrorShowroomStaging,
    [string]$BundleOut = "reports/patient_intake_fusion_bundle_latest.json",
    [string]$MyeongniOut = "reports/patient_intake_fusion_myeongni_latest.json",
    [string]$RationaleOut = "reports/patient_intake_fusion_rationale_latest.json"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($HarvestDryRunOnly) {
    py scripts/harvest_scm_boming_jiju_from_ijeoma_chunk_table_v1.py --apply --dry-run
    exit $LASTEXITCODE
}
if ($ApplyIjeomaHarvest) {
    py scripts/harvest_scm_boming_jiju_from_ijeoma_chunk_table_v1.py --apply
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if ($PruneIjeomaHarvestLexicon) {
    py scripts/prune_scm_boming_jiju_ijeoma_harvest_lexicon_v1.py --apply
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

py scripts/build_sasang_boming_jiju_clinical_lens_pack_v1.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

py scripts/build_patient_intake_fusion_draft_v1.py `
    --intake-json $IntakeJson `
    --bundle-out $BundleOut `
    --myeongni-out $MyeongniOut `
    --rationale-out $RationaleOut
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($IncludeTrackCDashboard) {
    py scripts/build_mkm_trackc_ops_dashboard_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
if ($IncludeShowroomTrustSlice) {
    $mirrorArg = @()
    if ($MirrorShowroomStaging) { $mirrorArg += "--mirror-staging" }
    py scripts/build_showroom_trust_visualization_slice_v1.py @mirrorArg
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    py scripts/validate_showroom_trust_slice_local_v1.py
}
exit $LASTEXITCODE
