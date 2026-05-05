# Ingest 3 external baseline results and rebuild adapter/table.
param(
    [string]$BaselineAJson = "docs/final/artifacts/sota_baseline_a_result_template.json",
    [string]$BaselineBJson = "docs/final/artifacts/sota_baseline_b_result_template.json",
    [string]$BaselineCJson = "docs/final/artifacts/sota_baseline_c_result_template.json"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

Write-Host "[1/3] Build SOTA adapter from baseline inputs" -ForegroundColor Cyan
& py "scripts/build_global_atom_sota_benchmark_adapter_v1.py" `
    "--baseline-a-json" $BaselineAJson `
    "--baseline-b-json" $BaselineBJson `
    "--baseline-c-json" $BaselineCJson `
    "--output-json" "docs/final/artifacts/global_atom_sota_benchmark_adapter_latest.json"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/3] Build Table-1 JSON/MD" -ForegroundColor Cyan
& py "scripts/build_global_atom_sota_table_v1.py" `
    "--adapter-json" "docs/final/artifacts/global_atom_sota_benchmark_adapter_latest.json" `
    "--output-json" "docs/final/artifacts/global_atom_sota_table_latest.json" `
    "--output-md" "docs/final/artifacts/global_atom_sota_table_latest.md"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[3/3] Build baseline readiness check" -ForegroundColor Cyan
& py "scripts/check_global_atom_sota_baseline_readiness_v1.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: SOTA baseline ingest chain complete." -ForegroundColor Green

