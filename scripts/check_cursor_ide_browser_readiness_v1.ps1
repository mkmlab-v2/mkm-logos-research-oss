#Requires -Version 5.1

<#

.SYNOPSIS

  Host-side readiness for Cursor IDE built-in browser (browser_* tools).



.DESCRIPTION

  cursor-ide-browser is NOT in .cursor/mcp.json.

  Newer Cursor builds use Browser MCP "direct execution" — mcps/cursor-ide-browser/tools/

  may be absent even when healthy. Parse Cursor IDE Browser Automation.log for root cause.



.PARAMETER Strict

  Exit 1 if host not ready for new chat probe.



.NOTES

  SSOT: docs/final/artifacts/cursor_ide_browser_automation_recovery_v1.json

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$McpsRoot = "",

    [string]$OutJson = "",

    [switch]$Strict

)



$ErrorActionPreference = "Stop"



function Resolve-CursorProjectMcpsRoot {

    param([string]$WorkspaceRootValue)

    if ($McpsRoot -and (Test-Path -LiteralPath $McpsRoot)) {

        return (Resolve-Path -LiteralPath $McpsRoot).Path

    }

    $leaf = Split-Path -Leaf $WorkspaceRootValue.TrimEnd('\', '/')

    $candidates = @(

        (Join-Path $env:USERPROFILE ".cursor\projects\c-workspace\mcps"),

        (Join-Path $env:USERPROFILE ".cursor\projects\$leaf\mcps")

    )

    foreach ($c in $candidates) {

        if (Test-Path -LiteralPath $c) { return $c }

    }

    return $null

}



function Find-LatestBrowserAutomationLog {

    $logsRoot = Join-Path $env:APPDATA "Cursor\logs"

    if (-not (Test-Path -LiteralPath $logsRoot)) { return $null }

    $files = Get-ChildItem -LiteralPath $logsRoot -Recurse -Filter "*Cursor IDE Browser Automation.log" -ErrorAction SilentlyContinue |

        Sort-Object LastWriteTime -Descending

    if ($files.Count -eq 0) { return $null }

    return $files[0].FullName

}



function Get-McpToolInventorySummary {

    param([string]$McpsRootPath)

    $servers = @()

    $total = 0

    if (-not $McpsRootPath -or -not (Test-Path -LiteralPath $McpsRootPath)) {

        return @{ servers = $servers; total_tool_count = 0; plugin_tool_count = 0 }

    }

    foreach ($dir in Get-ChildItem -LiteralPath $McpsRootPath -Directory) {

        $toolsDir = Join-Path $dir.FullName "tools"

        if (-not (Test-Path -LiteralPath $toolsDir)) { continue }

        $count = @(Get-ChildItem -LiteralPath $toolsDir -Filter "*.json" -ErrorAction SilentlyContinue).Count

        if ($count -le 0) { continue }

        $servers += [ordered]@{

            server_folder = $dir.Name

            tool_count    = $count

            is_plugin     = $dir.Name -like "plugin-*"

        }

        $total += $count

    }

    $pluginTotal = ($servers | Where-Object { $_.is_plugin } | ForEach-Object { $_.tool_count } | Measure-Object -Sum).Sum

    if ($null -eq $pluginTotal) { $pluginTotal = 0 }

    return @{

        servers            = ($servers | Sort-Object { -$_.tool_count })

        total_tool_count   = $total

        plugin_tool_count  = [int]$pluginTotal

    }

}



function Parse-BrowserAutomationLog {

    param([string]$LogPath)

    $result = [ordered]@{

        log_path               = $LogPath

        extension_activated    = $false

        direct_execution_mode  = $false

        no_browser_view_error  = $false

        provider_disposed      = $false

        last_error_line        = $null

    }

    if (-not $LogPath -or -not (Test-Path -LiteralPath $LogPath)) { return $result }

    $lines = Get-Content -LiteralPath $LogPath -Tail 120 -ErrorAction SilentlyContinue

    $lastNoViewAt = -1
    $lastToolExecAt = -1

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($line -match 'extension activated') { $result.extension_activated = $true }
        if ($line -match 'direct execution') { $result.direct_execution_mode = $true }
        if ($line -match 'No browser view available') {
            $lastNoViewAt = $i
            $result.last_error_line = $line.Trim()
        }
        if ($line -match 'Executing tool: browser_') { $lastToolExecAt = $i }
        if ($line -match 'MCP Provider disposed') { $result.provider_disposed = $true }
    }

    # Stale activation error is cleared once browser_* tools ran in the same log session.
    $result.no_browser_view_error = ($lastNoViewAt -ge 0) -and ($lastToolExecAt -lt $lastNoViewAt)

    return $result

}



$requiredTools = @(

    "browser_tabs",

    "browser_navigate",

    "browser_snapshot",

    "browser_lock",

    "browser_click"

)



$mcpPath = Join-Path $WorkspaceRoot ".cursor\mcp.json"

$mcpJsonOk = $false

$browserInMcpJson = @()

$mcpServers = @()

if (Test-Path -LiteralPath $mcpPath) {

    $mcpJsonOk = $true

    $mcp = Get-Content -LiteralPath $mcpPath -Raw | ConvertFrom-Json

    $mcpServers = @($mcp.mcpServers.PSObject.Properties.Name)

    $browserInMcpJson = @(

        "cursor-ide-browser",

        "browser",

        "cursor-browser"

    ) | Where-Object { $_ -in $mcpServers }

}



$mcpsRootResolved = Resolve-CursorProjectMcpsRoot -WorkspaceRootValue $WorkspaceRoot

$browserToolsDir = $null

$foundTools = @()

$missingTools = @()



if ($mcpsRootResolved) {

    $browserToolsDir = Join-Path $mcpsRootResolved "cursor-ide-browser\tools"

    if (Test-Path -LiteralPath $browserToolsDir) {

        foreach ($t in $requiredTools) {

            $f = Join-Path $browserToolsDir "$t.json"

            if (Test-Path -LiteralPath $f) { $foundTools += $t } else { $missingTools += $t }

        }

    } else {

        $missingTools = @($requiredTools)

    }

} else {

    $missingTools = @($requiredTools)

}



$descriptorsPresent = ($missingTools.Count -eq 0)

$browserLog = Parse-BrowserAutomationLog -LogPath (Find-LatestBrowserAutomationLog)

$toolInventory = Get-McpToolInventorySummary -McpsRootPath $mcpsRootResolved



$toolBudgetWarn = 40

$pluginBloat = $toolInventory.total_tool_count -gt 80

$mcpJsonLeanOk = $mcpJsonOk -and ($browserInMcpJson.Count -eq 0)



function Test-RecentBrowserHostAction {
    param(
        [string]$WorkspaceRootValue,
        [int]$MaxAgeMinutes = 15
    )
    $candidates = @(
        (Join-Path $WorkspaceRootValue "reports\cursor_ide_browser_warmup_latest.json"),
        (Join-Path $WorkspaceRootValue "reports\cursor_ide_browser_auto_fix_latest.json")
    )
    $now = (Get-Date).ToUniversalTime()
    foreach ($path in $candidates) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        try {
            $doc = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
            $tsRaw = [string]$doc.generated_at_utc
            if (-not $tsRaw) { continue }
            $ts = [datetime]::Parse($tsRaw).ToUniversalTime()
            if (($now - $ts).TotalMinutes -le $MaxAgeMinutes) { return $true }
        } catch { }
    }
    return $false
}



# Root cause ranking (Fact-Lock from Cursor logs + mcps inventory)

$rootCauses = @()

if ($browserLog.no_browser_view_error) {

    $rootCauses += "browser_view_missing"

}

if ($pluginBloat) {

    $rootCauses += "mcp_plugin_tool_bloat"

}

if (-not $browserLog.extension_activated) {

    $rootCauses += "browser_extension_not_activated"

}

if ($browserInMcpJson.Count -gt 0) {

    $rootCauses += "browser_wrongly_in_mcp_json"

}

if (-not $descriptorsPresent -and -not $browserLog.direct_execution_mode) {

    $rootCauses += "browser_mcp_descriptors_missing"

}



# Host ready: lean mcp.json + extension up + browser view error cleared + not plugin-saturated

$recentHostAction = Test-RecentBrowserHostAction -WorkspaceRootValue $WorkspaceRoot

$hostReady = $mcpJsonLeanOk -and $browserLog.extension_activated -and (-not $browserLog.no_browser_view_error) -and (-not $pluginBloat)

$warmupStampOverride = $false

if (-not $hostReady -and $recentHostAction -and $mcpJsonLeanOk -and $browserLog.extension_activated -and (-not $pluginBloat)) {

    $warmupStampOverride = $true

    $hostReady = $true

    $rootCauses = @($rootCauses | Where-Object { $_ -ne "browser_view_missing" })

}



$remediation = @()

if ($browserInMcpJson.Count -gt 0) {

    $remediation += "Remove cursor-ide-browser from .cursor/mcp.json (lean profile)"

}

if ($browserLog.no_browser_view_error) {

    $remediation += "Ctrl+Shift+J -> Tools and MCP -> Browser Automation -> Browser Tab (not Off)"

    $remediation += "Open Browser panel ONCE before new chat: Command Palette -> Cursor: Open Browser Tab, or @Browser in composer"

    $remediation += "Then Developer: Reload Window -> NEW Agent chat -> browser_tabs probe"

}

if ($pluginBloat) {

    $remediation += "Settings -> MCP: DISABLE unused Cursor plugins (NOT mcp.json): postman, atlassian, slack, datadog, sentry, cloudflare-* — target under 80 total MCP tools (~40 exposed per chat)"

    $remediation += "Keep .cursor/mcp.json lean 7 servers only; rerun scripts/Invoke-McpLeanProfileAlign_v1.ps1 if drift"

}

if ($remediation.Count -eq 0) {

    $remediation = @(

        "Start NEW Agent chat; first turn call browser_tabs (only success proves injection)",

        "Do NOT add cursor-ide-browser to .cursor/mcp.json"

    )

}



$recoverySsot = Join-Path $WorkspaceRoot "docs\final\artifacts\cursor_ide_browser_automation_recovery_v1.json"



$payload = [ordered]@{

    schema                  = "cursor_ide_browser_readiness_v2"

    generated_at_utc        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    workspace_root          = $WorkspaceRoot

    host_ready_for_new_chat = $hostReady

    warmup_stamp_override   = $warmupStampOverride

    root_causes             = $rootCauses

    injection_note          = $(if ($warmupStampOverride) {
        "warmup/autofix stamp within 15m — host likely ready; NEW chat browser_tabs is ground truth."
    } else {
        "mcps/cursor-ide-browser/tools absent may be normal with direct execution; chat browser_tabs success is ground truth."
    })

    mcp_json                = [ordered]@{

        path                   = $mcpPath

        exists                 = $mcpJsonOk

        servers                = $mcpServers

        lean_ok                = $mcpJsonLeanOk

        browser_server_in_json = ($browserInMcpJson.Count -gt 0)

    }

    mcps                    = [ordered]@{

        root                = $mcpsRootResolved

        browser_tools_dir   = $browserToolsDir

        required_tools      = $requiredTools

        found_tools         = $foundTools

        missing_tools       = $missingTools

        descriptors_present = $descriptorsPresent

        tool_inventory      = $toolInventory

        plugin_bloat        = $pluginBloat

        tool_budget_warn    = $toolBudgetWarn

    }

    browser_extension_log   = $browserLog

    recovery_ssot           = $recoverySsot

    remediation_steps       = $remediation

    verify_command          = "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check_cursor_ide_browser_readiness_v1.ps1"

}



if (-not $OutJson) {

    $OutJson = Join-Path $WorkspaceRoot "reports\cursor_ide_browser_readiness_latest.json"

}

$outDir = Split-Path -Parent $OutJson

if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {

    New-Item -ItemType Directory -Path $outDir -Force | Out-Null

}

$payload | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutJson -Encoding UTF8



Write-Host "=== Cursor IDE Browser readiness (v2) ===" -ForegroundColor Cyan

Write-Host "root_causes: $(if ($rootCauses.Count) { $rootCauses -join ', ' } else { '(none)' })"

Write-Host "mcp.json lean: $(if ($mcpJsonLeanOk) { 'ok' } else { 'FIX' }) ($($mcpServers.Count) servers)"

Write-Host "MCP tools total: $($toolInventory.total_tool_count) (plugin: $($toolInventory.plugin_tool_count))"

Write-Host "descriptors on disk: $(if ($descriptorsPresent) { 'present' } else { 'absent' })$(if ($browserLog.direct_execution_mode) { ' [direct execution — may be normal]' } else { '' })"

Write-Host "browser log: activated=$($browserLog.extension_activated) no_view=$($browserLog.no_browser_view_error)"

Write-Host "host_ready_for_new_chat: $hostReady"

Write-Host "Wrote: $OutJson"



if ($Strict -and -not $hostReady) { exit 1 }

if (-not $hostReady) { exit 2 }

exit 0

