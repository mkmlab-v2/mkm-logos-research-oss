#Requires -Version 5.1
<#
.SYNOPSIS
  Enforce MCP tool budget: mcp.json lean is not enough — prune Cursor plugin MCP bloat.

.DESCRIPTION
  Counts tools under %USERPROFILE%\.cursor\projects\c-workspace\mcps.
  If total > MaxTools or plugin-* servers present above threshold, runs:
    apply_cursor_mcp_plugin_diet_auto_v1.py + plugin mcps cache prune.

  SSOT complement: mcp_lean_profile only governs .cursor/mcp.json (7 servers).
  Plugin MCP (postman/atlassian/...) lives in Cursor Settings — this gate automates hygiene.

.PARAMETER MaxTools
  Fail/warn threshold (Cursor exposes ~40 tools/chat; 80 = headroom).

.PARAMETER AutoRemediate
  Apply diet + prune when over budget (default true).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MaxTools = 80,
    [switch]$AutoRemediate = $true,
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"

function Get-McpInventory {
    param([string]$McpsRoot)
    $servers = @()
    $total = 0
    $pluginTotal = 0
    if (-not (Test-Path -LiteralPath $McpsRoot)) {
        return @{ servers = $servers; total_tool_count = 0; plugin_tool_count = 0 }
    }
    foreach ($dir in Get-ChildItem -LiteralPath $McpsRoot -Directory) {
        $toolsDir = Join-Path $dir.FullName "tools"
        if (-not (Test-Path -LiteralPath $toolsDir)) { continue }
        $count = @(Get-ChildItem -LiteralPath $toolsDir -Filter "*.json" -ErrorAction SilentlyContinue).Count
        if ($count -le 0) { continue }
        $isPlugin = $dir.Name -like "plugin-*"
        $servers += [ordered]@{
            server_folder = $dir.Name
            tool_count    = $count
            is_plugin     = $isPlugin
        }
        $total += $count
        if ($isPlugin) { $pluginTotal += $count }
    }
    return @{
        servers           = $servers
        total_tool_count  = $total
        plugin_tool_count = $pluginTotal
    }
}

$mcps = Join-Path $env:USERPROFILE ".cursor\projects\c-workspace\mcps"
$before = Get-McpInventory -McpsRoot $mcps
$overBudget = $before.total_tool_count -gt $MaxTools
$remediated = $false
$remediationNote = $null

if ($overBudget -and $AutoRemediate) {
    $dietPy = Join-Path $WorkspaceRoot "scripts\apply_cursor_mcp_plugin_diet_auto_v1.py"
    if (Test-Path -LiteralPath $dietPy) {
        & py $dietPy
        if ($LASTEXITCODE -ne 0) { throw "apply_cursor_mcp_plugin_diet_auto_v1.py exit $LASTEXITCODE" }
    }
    if (Test-Path -LiteralPath $mcps) {
        foreach ($d in Get-ChildItem -LiteralPath $mcps -Directory -Filter "plugin-*") {
            Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $remediated = $true
    $remediationNote = "applied plugin diet + pruned plugin-* mcps cache"
}

$after = Get-McpInventory -McpsRoot $mcps
$stillOver = $after.total_tool_count -gt $MaxTools

if (-not $OutJson) {
    $OutJson = Join-Path $WorkspaceRoot "reports\mcp_plugin_tool_budget_gate_latest.json"
}
$outDir = Split-Path -Parent $OutJson
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$payload = [ordered]@{
    schema              = "mcp_plugin_tool_budget_gate_v1"
    generated_at_utc    = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    max_tools           = $MaxTools
    before              = $before
    after               = $after
    over_budget_before  = $overBudget
    over_budget_after   = $stillOver
    remediated          = $remediated
    remediation_note    = $remediationNote
    root_cause_note     = "mcp.json lean (7) is separate from Cursor Marketplace plugin-* MCP servers"
    verify_command      = 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-McpPluginToolBudgetGate_v1.ps1'
}
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutJson -Encoding UTF8

Write-Host "=== MCP plugin tool budget gate ===" -ForegroundColor Cyan
Write-Host "before: $($before.total_tool_count) tools (plugin $($before.plugin_tool_count))"
Write-Host "after : $($after.total_tool_count) tools (plugin $($after.plugin_tool_count))"
Write-Host "max   : $MaxTools"
Write-Host "Wrote: $OutJson"

if ($stillOver) { exit 1 }
exit 0
