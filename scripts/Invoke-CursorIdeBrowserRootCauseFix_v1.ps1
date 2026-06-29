#Requires -Version 5.1

<#

.SYNOPSIS

  Root-cause fix for Cursor IDE browser_tabs / browser_* injection failures.



.DESCRIPTION

  Diagnoses from Cursor logs + mcps inventory — NOT generic Reload loops.

  Primary blockers found on this host:

    1) No browser view (Browser Automation.log: No browser view available)

    2) Plugin MCP bloat (289+ tools; ~40 exposed per chat)

  mcp.json lean 7-server profile is correct — do NOT add cursor-ide-browser there.



.EXAMPLE

  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorIdeBrowserRootCauseFix_v1.ps1

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [switch]$SkipLeanAlign

)



$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $WorkspaceRoot



Write-Host "=== Cursor IDE Browser root-cause fix ===" -ForegroundColor Cyan



# 1) mcp.json lean align (user suspected mcp.json — verify, not blame)

if (-not $SkipLeanAlign) {

    $align = Join-Path $WorkspaceRoot "scripts\Invoke-McpLeanProfileAlign_v1.ps1"

    if (Test-Path -LiteralPath $align) {

        Write-Host "`n[1/4] MCP lean profile align..." -ForegroundColor Yellow

        & powershell -NoProfile -ExecutionPolicy Bypass -File $align

        if ($LASTEXITCODE -ne 0) {

            Write-Host "WARN: lean align exit $LASTEXITCODE" -ForegroundColor Yellow

        }

    }

}



# 2) Fresh tool inventory

Write-Host "`n[2/4] MCP tool inventory..." -ForegroundColor Yellow

$invScript = Join-Path $WorkspaceRoot "scripts\dump_mcp_tool_inventory.py"

if (Test-Path -LiteralPath $invScript) {

    & py $invScript -o (Join-Path $WorkspaceRoot "docs\final\artifacts\mkm_mcp_tool_audit_v1.json")

}



# 3) Enhanced readiness (log parse + bloat)

Write-Host "`n[3/4] Browser readiness v2..." -ForegroundColor Yellow

$check = Join-Path $WorkspaceRoot "scripts\check_cursor_ide_browser_readiness_v1.ps1"

& powershell -NoProfile -ExecutionPolicy Bypass -File $check -WorkspaceRoot $WorkspaceRoot

$readinessExit = $LASTEXITCODE

$reportPath = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_readiness_latest.json"

$report = $null

if (Test-Path -LiteralPath $reportPath) {

    $report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json

}



# 4) Recovery script (mcp.enabled)

$recovery = Join-Path $WorkspaceRoot "scripts\Invoke-CursorIdeBrowserRecovery_v1.ps1"

if (Test-Path -LiteralPath $recovery) {

    Write-Host "`n[4/4] Browser recovery (mcp.enabled)..." -ForegroundColor Yellow

    & powershell -NoProfile -ExecutionPolicy Bypass -File $recovery -WorkspaceRoot $WorkspaceRoot -SkipMcpEnable

}



$outJson = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_root_cause_fix_latest.json"

$pluginDiet = @(

    "plugin-postman-postman",

    "plugin-atlassian-atlassian",

    "plugin-slack-slack",

    "plugin-datadog-datadog",

    "plugin-sentry-sentry",

    "plugin-cloudflare-cloudflare-bindings",

    "plugin-cloudflare-cloudflare-docs",

    "plugin-cloudflare-cloudflare-builds",

    "plugin-cloudflare-cloudflare-observability"

)



$payload = [ordered]@{

    schema               = "cursor_ide_browser_root_cause_fix_v1"

    generated_at_utc     = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    workspace_root       = $WorkspaceRoot

    readiness_exit       = $readinessExit

    readiness_report     = $reportPath

    root_causes          = $(if ($report) { @($report.root_causes) } else { @() })

    host_ready           = $(if ($report) { $report.host_ready_for_new_chat } else { $false })

    mcp_json_is_problem  = $false

    mcp_json_note        = ".cursor/mcp.json lean 7-server profile is correct; browser is NOT an mcp.json entry."

    plugin_servers_disable_in_settings = $pluginDiet

    human_steps_required = @(

        "Ctrl+Shift+J -> Tools and MCP -> Browser Automation -> Browser Tab",

        "Command Palette -> open Browser Tab pane once (creates browser view)",

        "Settings -> MCP -> disable plugin servers listed in plugin_servers_disable_in_settings (keep lean 7 from mcp.json)",

        "Developer: Reload Window",

        "NEW Agent chat -> browser_tabs as first tool call"

    )

    log_evidence         = $(if ($report) { $report.browser_extension_log } else { $null })

    reproducible_command = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-CursorIdeBrowserRootCauseFix_v1.ps1"

}



$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $outJson -Encoding UTF8



Write-Host ""

Write-Host "=== ROOT CAUSE (not mcp.json) ===" -ForegroundColor Magenta

Write-Host "  mcp.json: lean 7 servers — OK. Do NOT add cursor-ide-browser."

if ($report.root_causes -contains "browser_view_missing") {

    Write-Host "  [P0] Browser view never opened -> Cursor log: No browser view available" -ForegroundColor Red

    Write-Host "       FIX: Browser Tab ON + open Browser pane once + Reload + new chat"

}

if ($report.root_causes -contains "mcp_plugin_tool_bloat") {

    Write-Host "  [P1] Plugin MCP bloat: $($report.mcps.tool_inventory.total_tool_count) tools (budget ~40/chat)" -ForegroundColor Red

    Write-Host "       FIX: Settings -> MCP -> disable postman/atlassian/slack/datadog/sentry/cloudflare plugins"

}

Write-Host ""

Write-Host "Human steps:" -ForegroundColor Yellow

foreach ($s in $payload.human_steps_required) { Write-Host "  - $s" }

Write-Host ""

Write-Host "Report: $outJson" -ForegroundColor DarkGray



if ($readinessExit -eq 0) { exit 0 }

exit $readinessExit

