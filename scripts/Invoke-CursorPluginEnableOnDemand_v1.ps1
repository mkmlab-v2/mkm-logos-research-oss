#Requires -Version 5.1
<#
.SYNOPSIS
  Temporarily enable a Cursor plugin MCP server (Customize on-demand).

.DESCRIPTION
  Removes one plugin id from disabledMcpServers in Cursor state.vscdb.
  Default diet keeps all plugins OFF; use per-lane from mkm_cursor_customize_mcp_v39_latest.json.

.PARAMETER Plugin
  Short name: atlassian | figma | slack | cloudflare-docs | exa | semgrep | all-off (re-sync diet)

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorPluginEnableOnDemand_v1.ps1 -Plugin figma
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "atlassian", "figma", "slack", "postman", "datadog", "sentry",
        "cloudflare-docs", "cloudflare-bindings", "cloudflare-builds", "cloudflare-observability",
        "exa", "linear", "semgrep", "sourcegraph", "all-off"
    )]
    [string]$Plugin,
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$map = @{
    "atlassian"               = "plugin-atlassian-atlassian"
    "figma"                   = "plugin-figma-figma"
    "slack"                   = "plugin-slack-slack"
    "postman"                 = "plugin-postman-postman"
    "datadog"                 = "plugin-datadog-datadog"
    "sentry"                  = "plugin-sentry-sentry"
    "cloudflare-docs"         = "plugin-cloudflare-cloudflare-docs"
    "cloudflare-bindings"     = "plugin-cloudflare-cloudflare-bindings"
    "cloudflare-builds"       = "plugin-cloudflare-cloudflare-builds"
    "cloudflare-observability" = "plugin-cloudflare-cloudflare-observability"
    "exa"                     = "plugin-exa-exa"
    "linear"                  = "plugin-linear-linear"
    "semgrep"                 = "plugin-semgrep-plugin-semgrep"
    "sourcegraph"             = "plugin-sourcegraph-cursor-plugin-sourcegraph"
}

if ($Plugin -eq "all-off") {
    $syncPy = Join-Path $WorkspaceRoot "scripts\persist_cursor_mcp_disabled_servers_v1.py"
    if ($WhatIf) {
        Write-Host "[WHATIF] py $syncPy sync --apply"
        exit 0
    }
    & py $syncPy sync --apply
    if ($LASTEXITCODE -ne 0) { throw "sync --apply exit $LASTEXITCODE" }
    Write-Host "[OK] All plugin MCP servers disabled (diet sync)." -ForegroundColor Green
    Write-Host "Reload Window required." -ForegroundColor Yellow
    exit 0
}

$serverId = $map[$Plugin]
$enablePy = Join-Path $WorkspaceRoot "scripts\enable_cursor_mcp_plugin_on_demand_v1.py"
if (-not (Test-Path -LiteralPath $enablePy)) { throw "Missing: $enablePy" }

if ($WhatIf) {
    Write-Host "[WHATIF] py $enablePy --server-id $serverId"
    exit 0
}

& py $enablePy --server-id $serverId
if ($LASTEXITCODE -ne 0) { throw "enable exit $LASTEXITCODE" }
Write-Host "[OK] Enabled plugin MCP: $serverId" -ForegroundColor Green
Write-Host "Reload Window required." -ForegroundColor Yellow
exit 0
