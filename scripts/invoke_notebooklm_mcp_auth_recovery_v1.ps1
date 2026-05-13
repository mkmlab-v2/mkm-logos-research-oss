<#
.SYNOPSIS
  NotebookLM MCP auth recovery helper (local-safe).

.DESCRIPTION
  Runs local prerequisites + profile lock repair + Korean UI selectors patch
  (idempotent), then prints the MCP recovery sequence for a **new chat** after
  **Reload Window**:
    1) setup_auth (if needed)
    2) get_health (authenticated=true)

  This script does not call NotebookLM MCP directly. It is safe to run
  before opening a new MCP auth flow.
#>
param(
    [switch]$SkipPrereqCheck,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$prereqScript = Join-Path $PSScriptRoot "check_notebooklm_mcp_prereqs.ps1"
$repairScript = Join-Path $PSScriptRoot "repair_notebooklm_mcp_auth_stuck.ps1"

Write-Host "=== NotebookLM MCP auth recovery helper ===" -ForegroundColor Cyan
Write-Host "repo root: $repoRoot"

if (-not $SkipPrereqCheck) {
    if (Test-Path -LiteralPath $prereqScript) {
        Write-Host "[1/4] prereq check" -ForegroundColor Yellow
        & $prereqScript -WorkspaceRoot $repoRoot
    } else {
        Write-Warning "prereq script not found: $prereqScript"
    }
} else {
    Write-Host "[1/4] prereq check skipped by flag" -ForegroundColor DarkGray
}

if (Test-Path -LiteralPath $repairScript) {
    Write-Host "[2/4] local profile lock repair" -ForegroundColor Yellow
    if ($WhatIfOnly) {
        & $repairScript -WhatIfOnly
    } else {
        & $repairScript
    }
} else {
    Write-Warning "repair script not found: $repairScript"
}

$koPatch = Join-Path $repoRoot "scripts\apply_notebooklm_mcp_ko_selectors_patch_v1.py"
if (Test-Path -LiteralPath $koPatch) {
    Write-Host "[3/4] Korean UI selectors patch (idempotent)" -ForegroundColor Yellow
    & py $koPatch
} else {
    Write-Warning "KO selectors patch script not found: $koPatch"
}

Write-Host ""
Write-Host "[4/4] In Cursor: Developer Reload Window, start a NEW chat, then MCP tools:" -ForegroundColor Yellow
Write-Host "  - setup_auth (if needed)"
Write-Host "  - get_health (authenticated=true)"
Write-Host "  - add_source should work after reload when NotebookLM UI is Korean."
Write-Host ""
Write-Host "Done." -ForegroundColor Green
