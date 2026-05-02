<#
.SYNOPSIS
  One-screen check: NotebookLM MCP env in .cursor/mcp.json (HEADLESS) + profile isolation reminder.
  Does not call Google; does not require Node. Exit 0 (warnings to stderr are non-fatal).
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = "Stop"
$mcpPath = Join-Path $WorkspaceRoot ".cursor\mcp.json"
if (-not (Test-Path -LiteralPath $mcpPath)) {
    Write-Host "OK: no .cursor/mcp.json at $mcpPath (skip)" -ForegroundColor DarkGray
    exit 0
}
$raw = Get-Content -LiteralPath $mcpPath -Raw -Encoding UTF8
$j = $raw | ConvertFrom-Json
$nb = $j.mcpServers.notebooklm
if (-not $nb) {
    Write-Host "OK: mcpServers.notebooklm not defined (skip)" -ForegroundColor DarkGray
    exit 0
}
$envN = $nb.env
$headless = $null
if ($envN) {
    $headless = $envN.HEADLESS
}
Write-Host "=== NotebookLM MCP prereq (repo) ===" -ForegroundColor Cyan
Write-Host "mcp.json: $mcpPath"
if ($null -eq $headless -or [string]::IsNullOrWhiteSpace([string]$headless)) {
    Write-Warning "notebooklm env.HEADLESS is not set. Default in notebooklm-mcp is headless=true; setup_auth may fail or show no window. Set HEADLESS=false under notebooklm.env (see docs/NotebookLM_sources_manifest.md)."
} elseif ([string]$headless -ne 'false') {
    Write-Warning "notebooklm env.HEADLESS='$headless'. Recommended 'false' for interactive setup_auth on Windows."
} else {
    Write-Host "HEADLESS=false: OK (visible Chrome for setup_auth)." -ForegroundColor Green
}
Write-Host ""
Write-Host "[FACT] MCP uses an isolated Chrome profile (not Cursor embedded browser login)." -ForegroundColor DarkYellow
Write-Host "  Windows profile dir (typical): `$env:APPDATA\notebooklm-mcp\chrome_profile\" -ForegroundColor DarkGray
Write-Host "SSOT: docs\NotebookLM_sources_manifest.md (MCP authentication section)" -ForegroundColor DarkGray
exit 0
