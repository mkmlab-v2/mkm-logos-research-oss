#Requires -Version 5.1
<#
.SYNOPSIS
  Fully automated Cursor IDE browser fix (host-side).

.DESCRIPTION
  1) MCP lean verify
  2) Disable bloated plugin MCP servers (disabledMcpServers in Cursor state)
  3) Set lastBrowserConnectionMode=editor
  4) Cursor CLI: open browser editor + reload window
  5) Re-run readiness v2

  After script: start NEW Agent chat for browser_tabs probe.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipReload
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

. (Join-Path $PSScriptRoot "Cursor-IdeBrowserCommon_v1.ps1")

Write-Host "=== Cursor IDE Browser AUTO fix ===" -ForegroundColor Cyan

$align = Join-Path $WorkspaceRoot "scripts\Invoke-McpLeanProfileAlign_v1.ps1"
if (Test-Path -LiteralPath $align) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $align | Out-Null
}

$dietPy = Join-Path $WorkspaceRoot "scripts\apply_cursor_mcp_plugin_diet_auto_v1.py"
& py $dietPy
if ($LASTEXITCODE -ne 0) { throw "apply_cursor_mcp_plugin_diet_auto_v1.py exit $LASTEXITCODE" }

$mcps = Join-Path $env:USERPROFILE ".cursor\projects\c-workspace\mcps"
if (Test-Path -LiteralPath $mcps) {
    $removed = @()
    foreach ($d in Get-ChildItem -LiteralPath $mcps -Directory -Filter "plugin-*") {
        Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction SilentlyContinue
        $removed += $d.Name
    }
    if ($removed.Count -gt 0) {
        Write-Host "Pruned plugin mcps cache: $($removed -join ', ')" -ForegroundColor Yellow
    }
}

Write-Host "Cursor CLI: pre-reload browser tab open..." -ForegroundColor Yellow
Open-CursorIdeBrowserTab -WorkspaceRoot $WorkspaceRoot
if (-not $SkipReload) {
    Invoke-CursorCli @("--reuse-window", $WorkspaceRoot, "--command", "workbench.action.reloadWindow")
    Write-Host "Reload Window sent — wait ~20s for MCP re-init..." -ForegroundColor Yellow
    Start-Sleep -Seconds 20
    & py $dietPy
    Write-Host "Post-reload: reopen Browser Tab (required for injectBrowserUIScript)..." -ForegroundColor Yellow
    Open-CursorIdeBrowserTab -WorkspaceRoot $WorkspaceRoot
    Start-Sleep -Seconds 5
}

$check = Join-Path $WorkspaceRoot "scripts\check_cursor_ide_browser_readiness_v1.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $check -WorkspaceRoot $WorkspaceRoot
$exitCode = $LASTEXITCODE

$outJson = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_auto_fix_latest.json"
$readiness = $null
$rp = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_readiness_latest.json"
if (Test-Path -LiteralPath $rp) {
    $readiness = Get-Content -LiteralPath $rp -Raw | ConvertFrom-Json
}

$payload = [ordered]@{
    schema           = "cursor_ide_browser_auto_fix_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    readiness_exit   = $exitCode
    host_ready       = $(if ($readiness) { $readiness.host_ready_for_new_chat } else { $false })
    root_causes      = $(if ($readiness) { @($readiness.root_causes) } else { @() })
    mcp_tool_count   = $(if ($readiness) { $readiness.mcps.tool_inventory.total_tool_count } else { $null })
    diet_report      = "reports/cursor_mcp_plugin_diet_auto_latest.json"
    next_step        = "NEW Agent chat -> browser_tabs"
    command          = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorIdeBrowserAutoFix_v1.ps1"
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outJson -Encoding UTF8

Write-Host ""
Write-Host "AUTO fix done. host_ready=$($payload.host_ready) tools=$($payload.mcp_tool_count) exit=$exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Yellow" })
Write-Host "Report: $outJson"
Write-Host "NEXT: NEW Agent chat -> browser_tabs" -ForegroundColor Cyan
exit $exitCode
