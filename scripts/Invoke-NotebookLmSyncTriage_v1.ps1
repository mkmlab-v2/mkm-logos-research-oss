<#
.SYNOPSIS
  One-screen triage: why "NotebookLM sync" feels broken (3 independent channels).

.DESCRIPTION
  Channel A — Vault mirror: copies repo files to MKM_DATA_VAULT (G: or MKM_VAULT_ROOT).
  Channel B — Google NotebookLM cloud: NOT automatic; UI source_add or push tasks only.
  Channel C — Cursor MCP: tools must inject per chat; separate Chrome profile for auth.

  This script does NOT call Google APIs or MCP. It only checks local prereqs + last mirror stamp.

.PARAMETER StrictVault
  Exit 1 if default vault path is not reachable (use when automation must hard-fail).

.PARAMETER RunMirror
  After triage, run sync_notebooklm_sources_to_mkm_data_vault.ps1 (not WhatIf).

.PARAMETER OutJson
  Optional path for a small triage JSON (default: reports/notebooklm_sync_triage_latest.json).
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$StrictVault,
    [switch]$RunMirror,
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"
$mcpExit = 0
$root = $WorkspaceRoot.TrimEnd('\')
$defaultVault = "G:\공유 드라이브\MKM_DATA_VAULT\vault"
$envVault = $env:MKM_VAULT_ROOT
$vaultRoot = if ($envVault -and $envVault.Trim()) { $envVault.Trim().TrimEnd('\') } else { $defaultVault }
$destMirror = Join-Path $vaultRoot "notebooklm_sources"
$stamp = Join-Path $destMirror "_LAST_SYNC.txt"
$manifest = Join-Path $root "docs\NotebookLM_sources_manifest.md"

Write-Host "=== NotebookLM 'sync' triage (3 channels) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "[A] Vault file mirror  ->  $destMirror" -ForegroundColor Yellow
$vaultOk = Test-Path -LiteralPath $vaultRoot
if (-not $vaultOk) {
    Write-Warning "Vault root not found: $vaultRoot  (set MKM_VAULT_ROOT or mount G: shared drive)"
    $channelA = "FAIL_UNREACHABLE"
} else {
    Write-Host "  Vault root OK: $vaultRoot" -ForegroundColor Green
    if (Test-Path -LiteralPath $stamp) {
        $t = (Get-Item -LiteralPath $stamp).LastWriteTimeUtc
        Write-Host "  _LAST_SYNC.txt: $([DateTime]$t) UTC" -ForegroundColor Green
        $channelA = "OK"
    } else {
        Write-Host "  _LAST_SYNC.txt: missing (mirror may never have run to this path)" -ForegroundColor DarkYellow
        $channelA = "STAMP_MISSING"
    }
}
Write-Host ""
Write-Host "[B] Google NotebookLM (cloud sources)" -ForegroundColor Yellow
Write-Host "  NOT auto-synced from Vault. Ingest = UI source_add, or scheduled push scripts." -ForegroundColor DarkGray
Write-Host "  SSOT in repo: $manifest" -ForegroundColor DarkGray
$channelB = "MANUAL_UI_OR_TASK"
Write-Host ""
Write-Host "[C] Cursor MCP (chat tools + auth)" -ForegroundColor Yellow
$prereq = Join-Path $root "scripts\check_notebooklm_mcp_prereqs.ps1"
if (Test-Path -LiteralPath $prereq) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $prereq -WorkspaceRoot $root
    $mcpExit = $LASTEXITCODE
    if ($mcpExit -eq 2) { $channelC = "MCP_CONFIG_ERROR" }
    elseif ($mcpExit -eq 1) { $channelC = "MCP_WARN_STRICT" }
    else { $channelC = "OK_OR_SKIPPED" }
} else {
    Write-Warning "Missing: $prereq"
    $channelC = "SCRIPT_MISSING"
    $mcpExit = 0
}

Write-Host ""
Write-Host "Recurrence prevention (read in order):" -ForegroundColor Cyan
Write-Host "  1) After changing mcp.json: Cursor Reload Window (old node process may keep old env)."
Write-Host "  2) New chat = new tool catalog; MCP green in Settings != tools in this chat."
Write-Host "  3) Web login != MCP auth; use setup_auth on isolated profile if get_health shows unauthenticated."
Write-Host "  4) Stale node >12h: repair_notebooklm_mcp_auth_stuck.ps1"
Write-Host "  5) Vault OK but cloud stale: run sync script then UI/task ingest (two different steps)."
Write-Host "SSOT: .cursor/rules/notebooklm-mcp-session-bridge.mdc + docs/NotebookLM_sources_manifest.md"
Write-Host ""

$summary = [ordered]@{
    schema              = "notebooklm_sync_triage_v1"
    generated_at_utc    = (Get-Date).ToUniversalTime().ToString("o")
    workspace_root      = $root
    vault_root          = $vaultRoot
    channel_a_vault     = $channelA
    channel_b_cloud     = $channelB
    channel_c_mcp       = $channelC
    last_sync_stamp_utc = if (Test-Path -LiteralPath $stamp) { (Get-Item -LiteralPath $stamp).LastWriteTimeUtc.ToString("o") } else { $null }
}
$jsonPath = $OutJson
if ([string]::IsNullOrWhiteSpace($jsonPath)) {
    $jsonPath = Join-Path $root "reports\notebooklm_sync_triage_latest.json"
}
$jsonDir = Split-Path -Parent $jsonPath
if (-not (Test-Path -LiteralPath $jsonDir)) { New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null }
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
Write-Host "Triage JSON: $jsonPath" -ForegroundColor DarkGray

if ($RunMirror) {
    $sync = Join-Path $root "scripts\sync_notebooklm_sources_to_mkm_data_vault.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $sync -WorkspaceRoot $root
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$exit = 0
if ($StrictVault -and -not $vaultOk) { $exit = 1 }
if ($mcpExit -eq 2) { $exit = 2 }
exit $exit
