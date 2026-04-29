param(
    [string]$BatchReportJson = "docs/final/artifacts/global_atom_full_canon_batch_report_latest.json",
    [string]$PreNewsInputJson = "docs/final/artifacts/pre_news_shadow_input_latest.json",
    [string]$OutputJson = "docs/final/artifacts/pre_news_shadow_projection_latest.json",
    [string]$LogJsonl = "reports/pre_news_shadow_projection_log.jsonl"
)

$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $workspaceRoot

& py "scripts/run_global_atom_pre_news_shadow_chain_v1.py" `
    "--batch-report-json" $BatchReportJson `
    "--pre-news-input-json" $PreNewsInputJson `
    "--output-json" $OutputJson `
    "--log-jsonl" $LogJsonl
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DONE: pre-news shadow projection generated." -ForegroundColor Green

