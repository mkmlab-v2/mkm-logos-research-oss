# One-click wrapper: v4 cursor transcript corpus -> compression intake -> dogfood briefing refresh.
# research_only / SEND_GATE HOLD. Local-only dogfood data.

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$TenantId = "mkm-internal-dogfood-v4-cursor",
    [string]$TranscriptJsonl = "",
    [int]$Rows = 24,
    [int]$MaxCases = 24,
    [switch]$SkipBuildCorpus,
    [switch]$SkipIntake,
    [switch]$SkipBriefingRefresh,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Set-Location -LiteralPath $WorkspaceRoot

$defaultTranscriptRoot = "C:\Users\PRO\.cursor\projects\c-workspace\agent-transcripts"
$relJsonl = "data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl"

Write-Host "=== Compression Dogfood V4 Cursor One-Click ===" -ForegroundColor Cyan
Write-Host "tenant: $TenantId | rows: $Rows | max_cases: $MaxCases | SEND_GATE HOLD" -ForegroundColor Yellow
Write-Host "research_only + internal dogfood only (no external SEND)" -ForegroundColor DarkYellow

if ($Rows -lt 20 -or $Rows -gt 30) {
    Write-Error "Rows must be in 20..30 (got $Rows)."
}
if ($MaxCases -lt 20 -or $MaxCases -gt 30) {
    Write-Error "MaxCases must be in 20..30 (got $MaxCases)."
}

if ($DryRun) {
    Write-Host "[DryRun] build_v4_corpus -> intake -> briefing_refresh" -ForegroundColor DarkGray
    exit 0
}

if (-not $SkipBuildCorpus) {
    Write-Host "=== Step 1/3: build v4 cursor transcript corpus ===" -ForegroundColor Cyan
    if ([string]::IsNullOrWhiteSpace($TranscriptJsonl)) {
        & py scripts/build_mkm_internal_dogfood_corpus_v4_cursor_transcripts.py --transcript-root $defaultTranscriptRoot --rows $Rows
    } else {
        & py scripts/build_mkm_internal_dogfood_corpus_v4_cursor_transcripts.py --transcript-jsonl $TranscriptJsonl --rows $Rows
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Step 1/3: skip corpus build ===" -ForegroundColor DarkGray
}

if (-not $SkipIntake) {
    Write-Host "=== Step 2/3: compression pilot intake ===" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-CompressionCustomerPilotIntake_v1.ps1 `
        -TenantId $TenantId `
        -CustomerJsonl $relJsonl `
        -MaxCases $MaxCases `
        -MinCases 20 `
        -RelaxPassGate
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Step 2/3: skip intake ===" -ForegroundColor DarkGray
}

if (-not $SkipBriefingRefresh) {
    Write-Host "=== Step 3/3: refresh compression dogfood briefing ===" -ForegroundColor Cyan
    & py scripts/build_compression_dogfood_briefing_v1.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "=== Step 3/3: skip briefing refresh ===" -ForegroundColor DarkGray
}

Write-Host "DONE: v4 cursor dogfood one-click completed." -ForegroundColor Green
Write-Host "jsonl: $relJsonl" -ForegroundColor Green
exit 0

