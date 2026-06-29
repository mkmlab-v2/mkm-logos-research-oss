#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot IDE Browser (browser_*) recovery — mcp.enabled + readiness report.

.NOTES
  Browser tools inject per chat after: Tools & MCP → Browser Automation ON → Reload → NEW chat.
  SSOT: docs/final/artifacts/cursor_ide_browser_automation_recovery_v1.json
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipMcpEnable
)

$ErrorActionPreference = "Stop"
$userSettings = Join-Path $env:APPDATA "Cursor\User\settings.json"

function Set-JsonBool {
    param([string]$Path, [string]$Key, [bool]$Value)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $literal = if ($Value) { "true" } else { "false" }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $pattern = '(?m)^\s*"' + [regex]::Escape($Key) + '"\s*:\s*.*$'
    $replacement = '  "' + $Key + '": ' + $literal + ','
    if ($raw -match $pattern) {
        $raw = [regex]::Replace($raw, $pattern, $replacement)
    } else {
        $raw = $raw -replace '(?s)\}\s*$', "`r`n$replacement`r`n}"
    }
    Set-Content -LiteralPath $Path -Value $raw -Encoding UTF8
    return $true
}

Write-Host "=== Cursor IDE Browser recovery ===" -ForegroundColor Cyan

if (-not $SkipMcpEnable) {
    $ok = Set-JsonBool -Path $userSettings -Key "mcp.enabled" -Value $true
    if ($ok) {
        Write-Host "Set mcp.enabled=true in $userSettings" -ForegroundColor Green
    } else {
        Write-Host "WARN: could not update mcp.enabled ($userSettings)" -ForegroundColor Yellow
    }
}

$check = Join-Path $WorkspaceRoot "scripts\check_cursor_ide_browser_readiness_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $check -WorkspaceRoot $WorkspaceRoot
$exit = $LASTEXITCODE

Write-Host ""
Write-Host "Required manual steps (agent cannot Reload Window for you):" -ForegroundColor Yellow
Write-Host "  1) Ctrl+Shift+J -> Tools & MCP -> Browser Automation -> ON (Browser Tab)"
Write-Host "  2) Command Palette -> Developer: Reload Window"
Write-Host "  3) Start a NEW chat -> first message: @Browser browser_tabs probe"
Write-Host ""
Write-Host "CF Logpush (Tier 3 Human Chrome — agent cannot log in):" -ForegroundColor DarkGray
Write-Host "  https://dash.cloudflare.com/?to=/:646e42cf881ab43043c32430e99d9af4/logs"
Write-Host ""

if ($exit -eq 0) {
    Write-Host "Descriptors PASS — new chat should have browser_* after Reload." -ForegroundColor Green
    exit 0
}
Write-Host "Descriptors still MISSING — complete steps 1-3 above, then rerun this script." -ForegroundColor Yellow
exit $exit
