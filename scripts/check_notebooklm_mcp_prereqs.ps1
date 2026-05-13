<#
.SYNOPSIS
  One-screen check: NotebookLM MCP prerequisites (mcp.json + global pin + stale process count + profile reminder).
  Does not call Google. Exit 0 by default; -Strict turns warnings into exit 1.

.DESCRIPTION
  Re-runnable gate (재발 방지 v1, 2026-05-09):
    1) mcp.json 'notebooklm' present
    2) command pinned (NOT 'npx -y ... @latest')
    3) HEADLESS=false (visible Chrome for setup_auth)
    4) MKM_NOTEBOOKLM_MCP_PINNED_VERSION env present (str)
    5) Global notebooklm-mcp installed at expected path; package.json version matches pinned (warn only if mismatch)
    6) Stale notebooklm-mcp node/cmd processes (>= StaleNodeMaxHours) count
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent $PSScriptRoot),
    [int]$StaleNodeMaxHours = 12,
    [int]$MaxStaleProcesses = 0,
    [switch]$Strict
)
$ErrorActionPreference = "Stop"
$warnings = @()
$errors   = @()

function Add-Warn($m) { $warnings += $m; Write-Warning $m }
function Add-Err($m)  { $errors   += $m; Write-Host "ERROR: $m" -ForegroundColor Red }

$mcpPath = Join-Path $WorkspaceRoot ".cursor\mcp.json"
Write-Host "=== NotebookLM MCP prereq (repo) ===" -ForegroundColor Cyan
Write-Host "mcp.json: $mcpPath"
if (-not (Test-Path -LiteralPath $mcpPath)) {
    Write-Host "OK: no .cursor/mcp.json (skip)" -ForegroundColor DarkGray
    exit 0
}
$raw = Get-Content -LiteralPath $mcpPath -Raw -Encoding UTF8
$j = $raw | ConvertFrom-Json
$nb = $j.mcpServers.notebooklm
if (-not $nb) {
    Write-Host "OK: mcpServers.notebooklm not defined (skip)" -ForegroundColor DarkGray
    exit 0
}

# (1)/(2) command pin check
$cmd = [string]$nb.command
$args = @()
if ($nb.args) { $args = @($nb.args) }
$argsJoined = ($args -join ' ')
$isNpxLatest = ($cmd -eq 'npx') -and ($argsJoined -match '@latest')
if ($isNpxLatest) {
    Add-Err "notebooklm.command='npx' with '@latest' detected. Pin to a fixed version OR call 'node <global path>/dist/index.js' directly."
} else {
    Write-Host "Command pin OK : command='$cmd' args='$argsJoined'" -ForegroundColor Green
}

# (3) HEADLESS env check
$envN = $nb.env
$headless = $null
if ($envN) { $headless = $envN.HEADLESS }
if ($null -eq $headless -or [string]::IsNullOrWhiteSpace([string]$headless)) {
    Add-Warn "notebooklm env.HEADLESS is not set. Default in notebooklm-mcp is headless=true; setup_auth may fail or show no window."
} elseif ([string]$headless -ne 'false') {
    Add-Warn "notebooklm env.HEADLESS='$headless'. Recommended 'false' for interactive setup_auth on Windows."
} else {
    Write-Host "HEADLESS=false  : OK (visible Chrome for setup_auth)." -ForegroundColor Green
}

# (4) pinned version env present
$pinnedEnv = $null
if ($envN) { $pinnedEnv = $envN.MKM_NOTEBOOKLM_MCP_PINNED_VERSION }
if ([string]::IsNullOrWhiteSpace([string]$pinnedEnv)) {
    Add-Warn "env.MKM_NOTEBOOKLM_MCP_PINNED_VERSION is empty. Set this string to the version you globally installed (audit trail only)."
} else {
    Write-Host "Pinned version env: $pinnedEnv" -ForegroundColor Green
}

# (5) global install + version match
$globalPkg = Join-Path $env:APPDATA "npm\node_modules\notebooklm-mcp\package.json"
$globalEntry = Join-Path $env:APPDATA "npm\node_modules\notebooklm-mcp\dist\index.js"
if (-not (Test-Path -LiteralPath $globalPkg)) {
    Add-Warn "Global notebooklm-mcp not installed at $globalPkg. Install with: npm i -g notebooklm-mcp@<version>"
} else {
    try {
        $pkg = Get-Content -LiteralPath $globalPkg -Raw -Encoding UTF8 | ConvertFrom-Json
        $installedVersion = [string]$pkg.version
        Write-Host "Global install   : v$installedVersion at $globalPkg" -ForegroundColor Green
        if ($pinnedEnv -and $installedVersion -and ($pinnedEnv -ne $installedVersion)) {
            Add-Warn "Pinned env ($pinnedEnv) != global installed ($installedVersion). Reinstall or update env."
        }
    } catch {
        Add-Warn "Failed to parse $globalPkg : $($_.Exception.Message)"
    }
    if (-not (Test-Path -LiteralPath $globalEntry)) {
        Add-Warn "Global entry missing: $globalEntry (reinstall recommended)"
    }
    # (5b) Korean UI selectors for add_source (upstream notebooklm-mcp 2.0.0 omits ko)
    $selJs = Join-Path $env:APPDATA "npm\node_modules\notebooklm-mcp\dist\notebooklm\selectors.js"
    if (Test-Path -LiteralPath $selJs) {
        try {
            $selRaw = Get-Content -LiteralPath $selJs -Raw -Encoding UTF8
            if ($selRaw -notmatch 'KO selectors \(MKM patch\)' -and $selRaw -notmatch 'Korean \(ko\)') {
                Add-Warn "notebooklm-mcp selectors.js may be missing Korean add_source anchors. Run: py scripts/apply_notebooklm_mcp_ko_selectors_patch_v1.py then Reload Window + new chat."
            }
        } catch {
            Add-Warn "Could not read selectors.js for KO patch check: $($_.Exception.Message)"
        }
    }
    # If command targets a path, ensure it exists
    if ($cmd -eq 'node' -and $args.Count -ge 1) {
        $target = $args[0]
        if ($target -and -not (Test-Path -LiteralPath $target)) {
            Add-Err "mcp.json node target not found: $target"
        }
    }
}

# (6) stale process scan
$cutoff = (Get-Date).AddHours(-1 * $StaleNodeMaxHours)
$stale = @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*notebooklm-mcp*' -and
    ($_.Name -in @('node.exe','cmd.exe')) -and
    ($_.CreationDate -lt $cutoff)
})
if ($stale.Count -gt $MaxStaleProcesses) {
    Add-Warn "Stale notebooklm-mcp node/cmd processes (>=${StaleNodeMaxHours}h): $($stale.Count). Run scripts/repair_notebooklm_mcp_auth_stuck.ps1 to clean."
} else {
    Write-Host "Stale procs (>=${StaleNodeMaxHours}h): $($stale.Count) (limit=$MaxStaleProcesses)" -ForegroundColor Green
}

Write-Host ""
Write-Host "[FACT] MCP uses an isolated Chrome profile (not Cursor embedded browser login)." -ForegroundColor DarkYellow
Write-Host "  Windows profile dir (typical): `$env:APPDATA\notebooklm-mcp\chrome_profile\" -ForegroundColor DarkGray
Write-Host "SSOT: docs\NotebookLM_sources_manifest.md  +  .cursor/rules/notebooklm-mcp-session-bridge.mdc" -ForegroundColor DarkGray

if ($errors.Count -gt 0)   { Write-Host ("Errors  : {0}" -f $errors.Count)   -ForegroundColor Red }
if ($warnings.Count -gt 0) { Write-Host ("Warnings: {0}" -f $warnings.Count) -ForegroundColor Yellow }

if ($errors.Count -gt 0) { exit 2 }
if ($Strict -and $warnings.Count -gt 0) { exit 1 }
exit 0
