<#
.SYNOPSIS
  NotebookLM MCP auth recovery helper (local-safe).

.DESCRIPTION
  Runs local prerequisites + profile lock repair, then prints the fixed
  MCP recovery sequence for this chat:
    1) setup_auth
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
        Write-Host "[1/3] prereq check" -ForegroundColor Yellow
        & $prereqScript -WorkspaceRoot $repoRoot
    } else {
        Write-Warning "prereq script not found: $prereqScript"
    }
} else {
    Write-Host "[1/3] prereq check skipped by flag" -ForegroundColor DarkGray
}

if (Test-Path -LiteralPath $repairScript) {
    Write-Host "[2/3] local profile lock repair" -ForegroundColor Yellow
    if ($WhatIfOnly) {
        & $repairScript -WhatIfOnly
    } else {
        & $repairScript
    }
} else {
    Write-Warning "repair script not found: $repairScript"
}

Write-Host ""
Write-Host "[3/3] MCP auth handshake (run in chat tools)" -ForegroundColor Yellow
Write-Host "  - Call: setup_auth"
Write-Host "  - Then: get_health"
Write-Host "  - Success condition: authenticated=true"
Write-Host ""
Write-Host "Done." -ForegroundColor Green
