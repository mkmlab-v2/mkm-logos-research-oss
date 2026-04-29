# Build end-to-end global atom submission pack artifacts.
param(
    [string]$OnepagerOutJson = "docs/final/artifacts/global_atom_network_academic_onepager_latest.json",
    [string]$AbstractsOutJson = "docs/final/artifacts/global_atom_network_submission_abstracts_latest.json",
    [string]$KddTemplateOutJson = "docs/final/artifacts/global_atom_kdd_submission_template_latest.json",
    [string]$BundleOutJson = "docs/final/artifacts/global_atom_submission_bundle_latest.json",
    [string]$FullCanonBatchReportJson = "docs/final/artifacts/global_atom_full_canon_batch_report_latest.json"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

Write-Host "[1/4] Build global atom academic one-pager" -ForegroundColor Cyan
& py "scripts/build_global_atom_network_onepager_v1.py" "--output-json" $OnepagerOutJson "--full-canon-batch-report-json" $FullCanonBatchReportJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/4] Build KDD/AAAI abstracts" -ForegroundColor Cyan
& py "scripts/build_global_atom_network_submission_abstracts_v1.py" "--onepager-json" $OnepagerOutJson "--output-json" $AbstractsOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/4] Build KDD template payload" -ForegroundColor Cyan
& py "scripts/build_global_atom_kdd_submission_template_v1.py" "--onepager-json" $OnepagerOutJson "--abstracts-json" $AbstractsOutJson "--output-json" $KddTemplateOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[4/4] Build submission bundle manifest" -ForegroundColor Cyan
& py "scripts/build_global_atom_submission_bundle_v1.py" "--output-json" $BundleOutJson
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: Global atom submission pack completed." -ForegroundColor Green

