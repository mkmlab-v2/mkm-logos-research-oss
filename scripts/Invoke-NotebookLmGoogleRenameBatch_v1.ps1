# Batch-rename Google NotebookLM web titles via nlm CLI (NOT MCP library.json).
# SSOT: docs/final/NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json
# Prereq: nlm login (admin@no1kmedi.com) — same profile as notebooklm-mcp pushes.
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Portfolio = Join-Path $Root 'docs\final\NOTEBOOKLM_MINIMAL_PORTFOLIO_V1.json'

if (-not (Get-Command nlm -ErrorAction SilentlyContinue)) {
    throw 'nlm not on PATH. npm i -g notebooklm-mcp and ensure nlm is available.'
}

$data = Get-Content -Raw -Encoding UTF8 $Portfolio | ConvertFrom-Json
$rows = @(
    $data.notebooks |
    Where-Object { $_.uuid -and $_.canonical_name } |
    Sort-Object { if ($null -eq $_.seq) { 999 } else { [int]$_.seq } }
)

Write-Host "== NotebookLM Google rename batch ($($rows.Count) notebooks) ==" -ForegroundColor Cyan
if ($DryRun) { Write-Host 'DRY RUN — no nlm calls' -ForegroundColor Yellow }

$fail = 0
foreach ($nb in $rows) {
    $uuid = $nb.uuid
    $title = $nb.canonical_name
    $legacy = $nb.legacy_name
    $prev = if ($nb.legacy_name) { $nb.legacy_name } else { $legacy }
    Write-Host "[$($nb.key)] $prev -> $title"
    if ($DryRun) { continue }
    & nlm notebook rename $uuid $title
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "FAILED: $($nb.key) exit=$LASTEXITCODE"
        $fail++
    }
    Start-Sleep -Milliseconds 400
}

# SBA archived notebook skipped by default (often NOT_FOUND on Google API)

if ($fail -gt 0) {
    Write-Host "DONE with $fail failure(s). Run: nlm login" -ForegroundColor Red
    exit 1
}
Write-Host 'DONE. Refresh notebooklm.google.com home (F5).' -ForegroundColor Green
exit 0
