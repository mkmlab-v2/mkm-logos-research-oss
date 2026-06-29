# Operator panel (internal dogfood) — build 30 sessions -> human gate -> intake -> panel gate (NOT customer/SEND).
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "wtt-operator-panel-v1",
    [string]$SourceJsonl = "",
    [string]$ConsentSourceRef = "docs/final/artifacts/fixtures/internal_panel_consent_v1.example.txt",
    [switch]$SkipBuild,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$exampleCorpus = Join-Path $WorkspaceRoot "data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl"
if ($SourceJsonl -eq "") {
    $SourceJsonl = $exampleCorpus
}

Write-Host "=== WTT Operator Panel Routine ===" -ForegroundColor Cyan
Write-Host "lane: operator_panel | NOT customer | SEND HOLD | not_eligible_for_send" -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "[DryRun] build -> human gate (lane) -> intake AllowOperatorPanel -> operator panel gate" -ForegroundColor DarkGray
    exit 0
}

if (-not $SkipBuild) {
    Write-Host "=== Step 1/4: build operator panel corpus ===" -ForegroundColor Cyan
    & py scripts/build_wtt_operator_panel_sessions_v1.py --out $exampleCorpus
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "=== Step 2/4: human gate (operator_panel lane) ===" -ForegroundColor Cyan
& py scripts/run_wtt_human_gate_interactive_v1.py `
    --tenant-id $TenantId `
    --source-jsonl $SourceJsonl `
    --lane operator_panel `
    --consent-type other `
    --consent-source-ref $ConsentSourceRef `
    --human-verified-by commander `
    --min-approve 30 `
    --approve-all `
    --public-facing-ok `
    --trigger-intake
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 3/4: operator panel gate (strict) ===" -ForegroundColor Cyan
& py scripts/check_wtt_operator_panel_gate_v1.py --tenant-id $TenantId --strict
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 4/4: refresh customer human_n30 report (operator rows excluded) ===" -ForegroundColor Cyan
& py scripts/check_wtt_human_n30_gate_v1.py --sync-pack
Write-Host "Note: customer human_n30_gate_met may stay false — operator panel is separate lane." -ForegroundColor DarkYellow

Write-Host "OK operator panel routine | gate: reports/wtt_operator_panel_gate_v1_latest.json" -ForegroundColor Green
exit 0
